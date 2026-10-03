import contextlib
import json
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
import service_path_check as tool
from report import write_report


@contextlib.contextmanager
def listener(tls=None):
    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen(1)
    server.settimeout(3)
    port = server.getsockname()[1]
    def accept():
        try:
            connection, _ = server.accept()
            with connection:
                if tls:
                    with tls.wrap_socket(connection, server_side=True):
                        pass
        except OSError:
            pass  # Invalid-cert tests deliberately abort the TLS handshake.
    thread = threading.Thread(target=accept, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.close()
        thread.join(4)


class ServiceTests(unittest.TestCase):
    def test_real_loopback_connection_and_child_resolver(self):
        with listener() as port:
            result = tool.check_service({'name': 'lab', 'host': '127.0.0.1', 'port': port}, 2)
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['addresses'][0]['tls'], 'not_requested')

    def test_refused_connection_is_tcp_failure(self):
        with socket.socket() as closed:
            closed.bind(('127.0.0.1', 0))
            port = closed.getsockname()[1]
        result = tool.check_service({'name': 'lab', 'host': '127.0.0.1', 'port': port}, 2)
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['dns']['status'], 'pass')
        self.assertEqual(result['addresses'][0]['tcp'], 'fail')

    def test_dns_deadline_does_not_claim_server_down(self):
        with patch.object(tool, 'resolve', side_effect=subprocess.TimeoutExpired('resolver', 1)):
            result = tool.check_service({'name': 'lab', 'host': 'lab.example.test', 'port': 443}, 1)
        self.assertEqual(result['failed_stage'], 'dns')
        self.assertEqual(result['addresses'], [])

    def test_mixed_addresses_do_not_get_green_pass(self):
        with listener() as port:
            addresses = [[socket.AF_INET, socket.SOCK_STREAM, 6, ['127.0.0.1', port]], [socket.AF_INET, socket.SOCK_STREAM, 6, ['127.0.0.2', port]]]
            with patch.object(tool, 'resolve', return_value=addresses):
                result = tool.check_service({'name': 'lab', 'host': 'localhost', 'port': port}, 1)
        self.assertEqual(result['status'], 'degraded')

    def test_intermittent_samples_are_not_hidden(self):
        with patch.object(tool, 'check_service', side_effect=[{'status': 'pass', 'addresses': []}, {'status': 'fail', 'failed_stage': 'dns', 'addresses': []}]):
            result = tool.run({'samples': 2, 'services': [{'name': 'lab', 'host': 'localhost', 'port': 443}]})
        self.assertEqual(result['findings'][0]['status'], 'degraded')
        self.assertEqual(result['status'], 'attention')

    def test_address_limit_is_reported(self):
        addresses = [[socket.AF_INET, socket.SOCK_STREAM, 6, ['127.0.0.2', 1]]] * 9
        with patch.object(tool, 'resolve', return_value=addresses):
            result = tool.check_service({'name': 'lab', 'host': 'localhost', 'port': 1}, .1)
        self.assertTrue(result['truncated_addresses'])
        self.assertEqual(len(result['addresses']), 8)

    def test_invalid_config_is_rejected_before_network(self):
        for values in [{'timeout': float('nan')}, {'samples': True}, {'timeout': 0}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                tool.validate_config({'services': [{'name': 'lab', 'host': 'localhost', 'port': 443}], **values})
        with self.assertRaises(ValueError):
            tool.validate_config({'services': [{'name': 'lab', 'host': 'https://localhost', 'port': 443}]})

    @unittest.skipUnless(shutil.which('openssl'), 'OpenSSL executable is needed for a real local TLS fixture')
    def test_real_tls_trust_and_hostname_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            cert, key = Path(temp) / 'cert.pem', Path(temp) / 'key.pem'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key), '-out', str(cert), '-days', '2', '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'], check=True, capture_output=True)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            for hostname, ca, expected in [('localhost', str(cert), 'pass'), ('wrong.example.test', str(cert), 'fail'), ('localhost', None, 'fail')]:
                with self.subTest(hostname=hostname, ca=ca), listener(context) as port:
                    addresses = [[socket.AF_INET, socket.SOCK_STREAM, 6, ['127.0.0.1', port]]]
                    with patch.object(tool, 'resolve', return_value=addresses):
                        result = tool.check_service({'name': 'lab', 'host': hostname, 'port': port, 'tls': True}, 2, ca)
                    self.assertEqual(result['addresses'][0]['tcp'], 'pass')
                    self.assertEqual(result['addresses'][0]['tls'], expected)

    def test_report_escapes_untrusted_strings(self):
        with tempfile.TemporaryDirectory() as temp:
            result = {'timestamp': 'now', 'status': 'attention', 'summary': '<script>bad</script>', 'findings': [{'item': '<img src=x onerror=bad>', 'status': 'fail'}]}
            output = write_report(result, Path(temp) / 'report', 'Lab')
            text = output.read_text()
            self.assertNotIn('<script>', text)
            self.assertNotIn('<img src=', text)
            self.assertIn('&lt;script&gt;', text)
            self.assertEqual(json.loads(output.with_suffix('.json').read_text()), result)


if __name__ == '__main__':
    unittest.main()

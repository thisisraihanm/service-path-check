import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import desktop
from friendly import explain, friendly_error, UserInputError
from report import write_report


class DesktopTests(unittest.TestCase):
    def test_offline_example_explained_without_claiming_repair(self):
        result = desktop.demo()
        headline, meaning, action = explain(result, desktop.TITLE)
        self.assertTrue(headline and meaning and action)
        self.assertNotIn('everything is healthy', (headline+meaning).lower())

    def test_example_label_and_plain_language_report(self):
        result = desktop.demo(); result['demo'] = True
        with tempfile.TemporaryDirectory() as temp:
            path = write_report(result, Path(temp)/'example', desktop.TITLE)
            page = path.read_text()
            self.assertIn('Fictional data', page)
            self.assertIn('What you can do next', page)
            self.assertIn('Details for IT support', page)
            self.assertNotIn('<script', page.lower())

    def test_actionable_validation_message(self):
        self.assertEqual(friendly_error(UserInputError('Choose both folders first.')), 'Choose both folders first.')
        self.assertIn('different computers', friendly_error(ValueError('Snapshots must describe the same host and platform')))
        self.assertIn('separate folders', friendly_error(ValueError('Source and backup must be separate, non-overlapping trees')))

    def test_real_widgets_and_async_example_when_display_available(self):
        import tkinter as tk
        try:
            root = tk.Tk(); root.destroy()
        except tk.TclError:
            self.skipTest('No desktop display in this environment; Windows packaging runs this check.')
        self.assertEqual(desktop.self_test(), 0)

    def test_website_input_defaults_and_login_rejection(self):
        values = {'host':'https://example.com/path?q=1','port':'9999','tls':False}
        service = desktop.make_config(values)['services'][0]
        self.assertEqual((service['host'], service['port'], service['tls']), ('example.com',443,True))
        values['host']='http://example.com:8080'; service=desktop.make_config(values)['services'][0]
        self.assertEqual((service['port'],service['tls']), (8080,False))
        for host in ('https://user:password@example.com','', 'ftp://example.com', 'server:445'):
            with self.subTest(host=host), self.assertRaises(ValueError):
                desktop.make_config({**values, 'host':host})

    def test_windowed_resolver_uses_file_protocol(self):
        import service_path_check as core
        import subprocess
        def child(command, **kwargs):
            self.assertIn('--resolve-worker', command)
            output = Path(command[-1]); output.write_text(json.dumps({'addresses':[[2,1,6,['127.0.0.1',443]]]}))
            return subprocess.CompletedProcess(command,0)
        with patch.object(core.sys,'executable','pythonw.exe'), patch.object(core.subprocess,'run',side_effect=child):
            addresses=core.resolve('localhost',443,1)
        self.assertEqual(addresses[0][3][0],'127.0.0.1')

    def test_resolver_file_protocol_preserves_failures(self):
        import service_path_check as core
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'dns.json'
            with patch.object(core,'resolve_worker',side_effect=OSError('name not found')):
                self.assertEqual(core.resolver_worker_file('bad',443,path),1)
            self.assertEqual(json.loads(path.read_text())['error'],'name not found')

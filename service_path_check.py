"""Diagnose only explicitly configured DNS -> TCP -> TLS service paths."""
import argparse
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import time

from report import write_report


def resolve_worker(host, port):
    records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    unique = {}
    for family, socktype, proto, _, address in records:
        unique[(family, address[0])] = [family, socktype, proto, list(address)]
    return list(unique.values())


def resolve(host, port, timeout):
    # An OS resolver can block beyond socket timeouts. A disposable child gives
    # DNS its own enforceable deadline without leaving background threads.
    command = [sys.executable, str(Path(__file__).resolve()), '--resolve', host, str(port)]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if completed.returncode:
        raise OSError(completed.stderr.strip() or 'Resolver failed')
    return json.loads(completed.stdout)


def validate_config(data):
    if not isinstance(data, dict) or set(data) - {'services', 'timeout', 'samples', 'ca_file'}:
        raise ValueError('Use services, timeout, samples, and optional ca_file only')
    services = data.get('services')
    if not isinstance(services, list) or not 1 <= len(services) <= 30:
        raise ValueError('Configure between 1 and 30 explicit services')
    timeout = data.get('timeout', 3)
    samples = data.get('samples', 1)
    if type(timeout) not in (int, float) or not 0.1 <= timeout <= 30:
        raise ValueError('timeout must be 0.1–30 seconds')
    if type(samples) is not int or not 1 <= samples <= 10:
        raise ValueError('samples must be an integer from 1 to 10')
    names = set()
    for s in services:
        if not isinstance(s, dict) or set(s) - {'name', 'host', 'port', 'tls'}:
            raise ValueError('Each service uses name, host, port, and optional tls')
        name, host, port = s.get('name'), s.get('host'), s.get('port')
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError('Service names must be nonempty and unique')
        names.add(name)
        if not isinstance(host, str) or not host or len(host) > 253 or any(c.isspace() for c in host) or any(c in host for c in '/\\@'):
            raise ValueError('host must be a DNS hostname or an IP address, not a URL')
        if ':' in host:
            ipaddress.IPv6Address(host)
        if type(port) is not int or not 1 <= port <= 65535 or type(s.get('tls', False)) is not bool:
            raise ValueError('port must be 1–65535; tls must be true or false')
    if data.get('ca_file') is not None and (not isinstance(data['ca_file'], str) or not Path(data['ca_file']).is_file()):
        raise ValueError('ca_file must point to an existing PEM CA certificate file')
    return data


def check_service(service, timeout, ca_file=None):
    observation = {'name': service['name'], 'host': service['host'], 'port': service['port'], 'tls_requested': service.get('tls', False), 'addresses': []}
    start = time.monotonic()
    try:
        addresses = resolve(service['host'], service['port'], timeout)
        if not addresses:
            raise OSError('Resolver returned no usable addresses')
        observation['dns'] = {'status': 'pass', 'elapsed_ms': round((time.monotonic() - start) * 1000, 2)}
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        observation.update(status='fail', failed_stage='dns', error=str(exc))
        observation['dns'] = {'status': 'fail'}
        return observation
    observation['truncated_addresses'] = len(addresses) > 8
    context = ssl.create_default_context(cafile=ca_file) if service.get('tls', False) else None
    for family, socktype, proto, address in addresses[:8]:
        item = {'ip': address[0], 'tcp': 'not_checked', 'tls': 'not_requested'}
        begin = time.monotonic()
        try:
            with socket.socket(family, socktype, proto) as connection:
                connection.settimeout(timeout)
                connection.connect(tuple(address))
                item['tcp'] = 'pass'
                item['tcp_ms'] = round((time.monotonic() - begin) * 1000, 2)
                if context:
                    item['tls'] = 'fail'
                    with context.wrap_socket(connection, server_hostname=service['host']) as secured:
                        item['tls'] = 'pass'
                        item['tls_version'] = secured.version()
                        item['certificate_expires'] = secured.getpeercert().get('notAfter')
        except (OSError, ValueError) as exc:
            if item['tcp'] != 'pass':
                item['tcp'] = 'fail'
            item['error'] = str(exc)
        observation['addresses'].append(item)
    passes = sum(x['tcp'] == 'pass' and x['tls'] in ('pass', 'not_requested') for x in observation['addresses'])
    observation['status'] = 'pass' if passes == len(observation['addresses']) and not observation['truncated_addresses'] else ('degraded' if passes else 'fail')
    return observation


def run(config):
    config = validate_config(config)
    observations = []
    findings = []
    for service in config['services']:
        checks = [check_service(service, config.get('timeout', 3), config.get('ca_file')) for _ in range(config.get('samples', 1))]
        observations.extend(checks)
        successes = sum(c['status'] == 'pass' for c in checks)
        status = 'pass' if successes == len(checks) else ('degraded' if successes or any(c['status'] == 'degraded' for c in checks) else 'fail')
        advice = 'Path checks passed; application login, permissions, and functionality still require testing.'
        if status != 'pass':
            if any(c.get('failed_stage') == 'dns' for c in checks):
                advice = 'Check configured DNS, VPN context, and hostname spelling. A DNS error does not prove the server is down.'
            elif any(a['tcp'] == 'fail' for c in checks for a in c['addresses']):
                advice = 'Check route, listener, and firewall policy for the affected IP. Connection failure alone cannot identify the cause.'
            else:
                advice = 'Inspect certificate name, validity, trust chain, system clock, or protocol mismatch; keep validation enabled.'
            if any(c.get('truncated_addresses') for c in checks):
                advice += ' More than eight addresses were resolved; unchecked addresses prevent a full pass.'
        findings.append({'status': status, 'item': service['name'], 'evidence': f'{successes}/{len(checks)} samples passed every configured stage. See per-address evidence below.', 'next_step': advice})
    status = 'pass' if all(f['status'] == 'pass' for f in findings) else 'attention'
    return {'schema_version': 1, 'timestamp': datetime.now(timezone.utc).isoformat(), 'status': status, 'summary': 'DNS, TCP, and optional verified TLS observations from this machine. This is not an application health or uptime guarantee.', 'findings': findings, 'observations': observations}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path)
    p.add_argument('--demo', action='store_true', help='Render synthetic results without any network traffic')
    p.add_argument('--output', default='reports/service-path')
    args = p.parse_args()
    try:
        if args.demo and args.config:
            p.error('Choose --demo or --config')
        if args.demo:
            result = json.loads((Path(__file__).parent / 'examples/demo-result.json').read_text(encoding='utf-8'))
        elif args.config:
            config = json.loads(args.config.read_text(encoding='utf-8-sig'))
            if not isinstance(config, dict):
                raise ValueError('Configuration must be a JSON object')
            if config.get('ca_file'):
                if not isinstance(config['ca_file'], str):
                    raise ValueError('ca_file must be a file path string')
                config['ca_file'] = str((args.config.parent / config['ca_file']).resolve())
            result = run(config)
        else:
            p.error('Choose --demo or --config FILE')
        report = write_report(result, args.output, 'Service Path Check')
        print(f"{result['status'].upper()}: {report}")
        return 0 if result['status'] == 'pass' else 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--resolve':
        try:
            print(json.dumps(resolve_worker(sys.argv[2], int(sys.argv[3]))))
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)
    else:
        sys.exit(main())

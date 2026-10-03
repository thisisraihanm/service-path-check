import ipaddress
import json
from pathlib import Path
import socket
import sys
from urllib.parse import urlsplit
from service_path_check import run, resolve, resolver_worker_file
from desktop_ui import App, resource_root
from friendly import UserInputError
TITLE = 'Service Path Check'
KIND = 'service'


def make_config(values):
    text = values['host'].strip()
    if not text: raise UserInputError('Enter a website address or server name first.')
    if '://' in text:
        parsed = urlsplit(text)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise UserInputError('Use a normal http:// or https:// address without a username or password.')
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        tls = parsed.scheme == 'https'
    else:
        host = text
        try: ipaddress.ip_address(host)
        except ValueError:
            if ':' in host:
                raise UserInputError('For a custom port, enter only the server name and use Connection options. Put IPv6 addresses in without a port.')
        try: port = int(values['port'])
        except ValueError: raise UserInputError('The port must be a number. Ask IT for the right port, or select a website preset.')
        tls = values['tls']
    from service_path_check import validate_config
    return validate_config({'services': [{'name': host, 'host': host, 'port': port, 'tls': tls}], 'samples': 3, 'timeout': 3})


def check(values): return run(make_config(values))
def demo(): return json.loads((resource_root() / 'examples/demo-result.json').read_text(encoding='utf-8'))
def make_app(window): return App(window, KIND, TITLE, demo, check)
def extra_smoke():
    assert resolve('127.0.0.1', 443, 3)
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0)); server.listen(2)
        result = run({'services': [{'name': 'Local test', 'host': '127.0.0.1', 'port': server.getsockname()[1]}], 'samples': 1})
        assert result['status'] == 'pass', result


def self_test(result_path=None):
    import tempfile
    import time
    import tkinter as tk
    import desktop_ui
    try:
        with tempfile.TemporaryDirectory() as directory:
            desktop_ui.data_root = lambda: Path(directory)
            window = tk.Tk(); window.withdraw()
            app = make_app(window)
            app.start_demo()
            deadline = time.monotonic() + 20
            while app.busy and time.monotonic() < deadline:
                window.update(); time.sleep(0.02)
            assert not app.busy and app.report and app.report.exists(), 'Example did not finish'
            assert app.result.get('demo') is True
            assert str(app.run_button.cget('state')) == 'normal'
            window.destroy()
            extra_smoke()
        result = {'ok': True, 'tool': TITLE, 'checks': ['desktop window', 'example', 'report', 'controls restored', 'engine smoke']}
        code = 0
    except Exception as error:
        result = {'ok': False, 'tool': TITLE, 'error': str(error)}
        code = 1
    if result_path: Path(result_path).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return code


def main():
    import tkinter as tk
    if '--self-test' in sys.argv:
        index = sys.argv.index('--self-test')
        return self_test(sys.argv[index+1] if len(sys.argv) > index+1 else None)
    window = tk.Tk()
    app = make_app(window)
    if '--preview' in sys.argv: window.after(200, app.start_demo)
    window.mainloop()
    return 0


if __name__ == '__main__':
    if KIND == 'service' and len(sys.argv) == 5 and sys.argv[1] == '--resolve-worker':
        sys.exit(resolver_worker_file(*sys.argv[2:]))
    sys.exit(main())

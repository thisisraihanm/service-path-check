"""Build and smoke-test the Windows app; run on Windows with PyInstaller installed."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

APP = 'ServicePathCheck'
VERSION = '1.1.0'
ROOT = Path(__file__).resolve().parent


def main():
    if sys.platform != 'win32': raise SystemExit('Windows apps must be built on Windows.')
    dist = ROOT / 'dist'; dist.mkdir(exist_ok=True)
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
               '--name', APP, '--add-data', 'examples:examples']
    if (ROOT / 'Collect-Snapshot.ps1').exists(): command += ['--add-data', 'Collect-Snapshot.ps1:.']
    command.append('desktop.py')
    subprocess.run(command, cwd=ROOT, check=True)
    executable = dist / (APP + '.exe')
    smoke = dist / 'packaged-smoke.json'
    completed = subprocess.run([str(executable), '--self-test', str(smoke)], timeout=90)
    if completed.returncode or not smoke.exists() or not json.loads(smoke.read_text())['ok']:
        raise SystemExit('Packaged desktop smoke check failed; no release archive created.')
    instructions = ('OPEN ' + APP + '.exe TO START\n\n'
        '1. Double-click the app. Python is already included.\n'
        '2. Click Try a safe example first.\n'
        '3. Follow the Choose what to check screen for your own check.\n'
        '4. Read the result. Use Open detailed report or Save report copy when needed.\n\n'
        'These tools read and report. They do not repair settings, copy backups, or delete files.\n'
        'Reports are saved locally and may contain server or file names. Share with your IT support when needed.\n'
        'Windows settings collection respects the current PowerShell script policy.\n'
        'The app is not code-signed. If Windows or company policy blocks it, ask IT to review it.\n')
    archive = dist / (APP + '-Windows.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        output.write(executable, executable.name)
        output.write(ROOT / 'LICENSE', 'LICENSE.txt')
        output.writestr('START-HERE.txt', instructions)
        output.writestr('BUILD-INFO.json', json.dumps({'version': VERSION, 'app': APP,
            'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(), 'packaged_smoke': json.loads(smoke.read_text())}, indent=2))
    print('Verified Windows archive: ' + str(archive))


if __name__ == '__main__': main()

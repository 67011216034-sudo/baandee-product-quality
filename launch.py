"""Windows/local launcher; checks Python and prepares isolated dependencies."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV = ROOT / '.venv'
VENV_PYTHON = VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def required_version():
    for line in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines():
        if line.strip().startswith('streamlit=='):
            return line.strip().split('==', 1)[1]
    raise RuntimeError('requirements.txt must pin a Streamlit version')


def dependency_ready(executable, environment):
    probe = (
        'import streamlit, streamlit.web.cli; '
        'from importlib.metadata import version; '
        f'assert version("streamlit") == {required_version()!r}'
    )
    result = subprocess.run(
        [str(executable), '-c', probe], cwd=ROOT, env=environment,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
    )
    return result.returncode == 0


def prepare(environment):
    # Extracted copies do not depend on the authoring workspace or work/ runtime.
    if dependency_ready(sys.executable, environment):
        return Path(sys.executable)
    if not VENV_PYTHON.exists():
        print('Creating a local .venv (no administrator rights needed)...', flush=True)
        subprocess.run([sys.executable, '-m', 'venv', str(VENV)], cwd=ROOT, env=environment, check=True)
    isolated = environment.copy()
    isolated.pop('PYTHONPATH', None)
    isolated.pop('PYTHONHOME', None)
    if not dependency_ready(VENV_PYTHON, isolated):
        print('Installing requirements into .venv. Internet is needed on first launch.', flush=True)
        subprocess.run(
            [str(VENV_PYTHON), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')],
            cwd=ROOT, env=isolated, check=True,
        )
    if not dependency_ready(VENV_PYTHON, isolated):
        raise RuntimeError('Dependency check failed; see GETTING_STARTED.md')
    environment.clear()
    environment.update(isolated)
    return VENV_PYTHON


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='Report readiness without installs or starting a server')
    action.add_argument('--setup-only', action='store_true', help='Prepare dependencies without starting the app')
    parser.add_argument('--legacy', action='store_true', help='Run the original standard-library HTML/API app')
    parser.add_argument('--no-browser', action='store_true', help='Do not open a browser')
    parser.add_argument('--port', type=int, default=8501)
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        print('Python 3.10+ is required; Python 3.12 is recommended.', file=sys.stderr)
        return 1
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    environment = os.environ.copy()
    if args.check:
        ready = args.legacy or dependency_ready(sys.executable, environment)
        print(json.dumps({
            'python': sys.executable, 'python_version': sys.version.split()[0],
            'project': str(ROOT), 'dependencies_ready': ready,
            'setup_needed': not ready, 'venv_exists': VENV_PYTHON.exists(),
        }, indent=2))
        return 0 if ready else 1
    print('BaanDee Quality Studio', flush=True)
    print('Python: ' + sys.executable, flush=True)
    executable = Path(sys.executable) if args.legacy else prepare(environment)
    if args.setup_only:
        print('Setup complete. Run start_streamlit.bat to open the local app.', flush=True)
        return 0
    if args.legacy:
        command = [str(executable), str(ROOT / 'app.py')]
    else:
        print(f'Local app: http://localhost:{args.port}', flush=True)
        print('Keep this window open. Press Ctrl+C to stop.', flush=True)
        command = [str(executable), '-m', 'streamlit', 'run', str(ROOT / 'streamlit_app.py'),
                   '--server.address=127.0.0.1', f'--server.port={args.port}',
                   '--server.headless=' + ('true' if args.no_browser else 'false')]
    return subprocess.run(command, cwd=ROOT, env=environment).returncode


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nStopped.')
        raise SystemExit(0)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('\nStartup failed: ' + str(error), file=sys.stderr)
        print('See GETTING_STARTED.md or use https://baandee-quality-studio.streamlit.app/', file=sys.stderr)
        raise SystemExit(1)

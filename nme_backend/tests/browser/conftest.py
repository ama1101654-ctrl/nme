from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from contextlib import closing
from pathlib import Path
from shutil import which

import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = WORKSPACE_ROOT / 'nme_backend'
FRONTEND_ROOT = WORKSPACE_ROOT / 'nme_frontend'
TEST_LOG_DIR = Path(tempfile.mkdtemp(prefix='nme-browser-logs-'))


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _wait_for_http(url: str, expected_substring: str | None = None, timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    last_error: str | None = None

    while time.time() < deadline:
        try:
            request = urllib.request.Request(url, headers={'Accept': 'text/html,application/xhtml+xml'})
            with urllib.request.urlopen(request, timeout=3) as response:
                payload = response.read().decode('utf-8', errors='ignore')
                if expected_substring is None or expected_substring in payload:
                    return
                last_error = f'expected {expected_substring!r} not found in response from {url}'
        except Exception as exc:  # pragma: no cover - readiness polling only
            last_error = str(exc)

        time.sleep(0.5)

    raise RuntimeError(f'Timed out waiting for {url}: {last_error}')


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


@pytest.fixture(scope='session')
def browser_runtime():
    backend_port = _free_port()
    frontend_port = _free_port()
    backend_url = f'http://127.0.0.1:{backend_port}'
    frontend_url = f'http://127.0.0.1:{frontend_port}'

    backend_log_path = TEST_LOG_DIR / 'backend.log'
    frontend_log_path = TEST_LOG_DIR / 'frontend.log'

    backend_env = os.environ.copy()
    frontend_env = os.environ.copy()
    backend_env['PYTHONUNBUFFERED'] = '1'
    backend_env['DEV_CORS_ALLOW_ORIGINS'] = frontend_url
    frontend_env['VITE_API_URL'] = backend_url

    backend_python = BACKEND_ROOT / '.venv' / 'Scripts' / 'python.exe'
    backend_python_cmd = str(backend_python if backend_python.exists() else Path(sys.executable))
    npm_cmd = which('npm.cmd') or which('npm') or 'npm.cmd'

    backend_cmd = [
        backend_python_cmd,
        '-m',
        'uvicorn',
        'app.main:app',
        '--host',
        '127.0.0.1',
        '--port',
        str(backend_port),
        '--no-proxy-headers',
    ]
    frontend_cmd = [
        npm_cmd,
        'run',
        'dev',
        '--',
        '--host',
        '127.0.0.1',
        '--port',
        str(frontend_port),
    ]

    backend_stream = backend_log_path.open('w', encoding='utf-8')
    frontend_stream = frontend_log_path.open('w', encoding='utf-8')
    backend_process: subprocess.Popen[str] | None = None
    frontend_process: subprocess.Popen[str] | None = None

    try:
        backend_process = subprocess.Popen(
            backend_cmd,
            cwd=str(BACKEND_ROOT),
            env=backend_env,
            stdout=backend_stream,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _wait_for_http(f'{backend_url}/health', expected_substring='"status":"ok"')

        frontend_process = subprocess.Popen(
            frontend_cmd,
            cwd=str(FRONTEND_ROOT),
            env=frontend_env,
            stdout=frontend_stream,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _wait_for_http(frontend_url)

        yield {
            'backend_url': backend_url,
            'frontend_url': frontend_url,
            'backend_log_path': backend_log_path,
            'frontend_log_path': frontend_log_path,
        }
    finally:
        if frontend_process is not None:
            _terminate_process(frontend_process)
        if backend_process is not None:
            _terminate_process(backend_process)
        frontend_stream.close()
        backend_stream.close()


@pytest.fixture(scope='session')
def browser_backend_url(browser_runtime):
    return browser_runtime['backend_url']


@pytest.fixture(scope='session')
def browser_frontend_url(browser_runtime):
    return browser_runtime['frontend_url']

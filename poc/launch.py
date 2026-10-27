#!/usr/bin/env python3
"""Launch the verified local codec, model runtime, and browser from one command."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen
import webbrowser

import p2p

ROOT = Path(__file__).resolve().parent.parent


def model_path():
    return Path(os.environ.get('OLLAMA_MODELS', str(Path.home() / '.ollama/models'))) / 'blobs' / ('sha256-' + p2p.MODEL_SHA)


def prepare_model(download=True):
    # Check runtime availability before initiating a large download.
    binary = p2p.locate_server()
    model = model_path()
    if not model.is_file():
        ollama = shutil.which('ollama')
        if not download:
            raise p2p.CodecError(f'Model is missing. Run: ollama pull {p2p.MODEL}')
        if not ollama:
            raise p2p.CodecError('Install and start Ollama first. Setup: https://github.com/jchook/plaintext-to-plaintext/blob/main/poc/README.md#setup')
        print('Downloading the pinned model with Ollama (about 2 GB)…', flush=True)
        subprocess.run([ollama, 'pull', p2p.MODEL], check=True)
    if not model.is_file():
        raise p2p.CodecError('The model is not in this model store. Set OLLAMA_MODELS to the directory used by your running Ollama service.')
    digest = hashlib.sha256()
    with model.open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != p2p.MODEL_SHA:
        raise p2p.CodecError('The model file does not match the verified SHA-256. Restore the pinned model before starting.')
    return binary, model


def endpoint_alive(url):
    try:
        with urlopen(url.rstrip('/') + '/props', timeout=2):
            return True
    except HTTPError:
        return True  # Something owns the port; do not replace it.
    except URLError:
        return False


def wait_ready(url, child, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise p2p.CodecError('A server exited during startup. Read its output above and check the setup guide.')
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, OSError):
            pass
        time.sleep(.25)
    raise p2p.CodecError('Server startup timed out. Check the runtime or increase --startup-timeout.')


def stop(child):
    if child is None or child.poll() is not None:
        return
    try:
        child.terminate()
    except ProcessLookupError:
        return
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Attach an existing compatible model server; do not download or start one')
    parser.add_argument('--port', type=int, default=8000, help='Local web port')
    parser.add_argument('--queue-size', type=int, default=20)
    parser.add_argument('--startup-timeout', type=float, default=90)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--check', action='store_true', help='Check runtime and pinned model without downloading or starting servers')
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535 or args.queue_size < 1 or args.startup_timeout <= 0:
        parser.error('Port, queue size, and startup timeout must be positive and the port must be at most 65535.')
    if args.url:
        url = urlsplit(args.url)
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
            parser.error('--url must be an HTTP(S) endpoint without credentials, query, or fragment.')
    return args


def main(argv=None):
    args = parse_args(argv)
    owned_model = owned_web = None
    try:
        if args.check:
            if args.url:
                if not endpoint_alive(args.url):
                    raise p2p.CodecError('The configured inference endpoint is unavailable.')
                print('Endpoint reachable. Start without --check to verify model identity and exact replay.')
            else:
                binary, _ = prepare_model(download=False)
                print(f'Runtime found: {binary}\nPinned model checksum verified. Start without --check to verify API compatibility and exact replay.')
            return 0
        # Fail early if the web port is already in use.
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', args.port))
        model_url = args.url or p2p.DEFAULT_URL
        if not endpoint_alive(model_url):
            if args.url:
                raise p2p.CodecError('The configured model endpoint is unavailable. Start that server, then retry.')
            prepare_model()
            print('Starting the dedicated local CPU model…', flush=True)
            owned_model = subprocess.Popen([sys.executable, str(ROOT / 'poc/p2p.py'), 'serve'], cwd=ROOT, start_new_session=True)
            wait_ready(model_url + '/health', owned_model, args.startup_timeout)
        print('Checking model identity and exact replay…', flush=True)
        with p2p.server_lock(model_url):
            p2p.probe(model_url)
        owned_web = subprocess.Popen([sys.executable, str(ROOT / 'poc/web_demo.py'), '--url', model_url,
            '--port', str(args.port), '--queue-size', str(args.queue_size)], cwd=ROOT, start_new_session=True)
        web_url = f'http://127.0.0.1:{args.port}'
        wait_ready(web_url + '/api/config', owned_web, args.startup_timeout)
        print(f'\nReady: {web_url}\nPress Ctrl-C to stop the servers started by this launcher.', flush=True)
        if not args.no_browser:
            webbrowser.open(web_url)
        return owned_web.wait()
    except KeyboardInterrupt:
        print('\nStopping the local demo…', flush=True)
        return 0
    except (p2p.CodecError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'error: {error}\nSetup guide: https://github.com/jchook/plaintext-to-plaintext/blob/main/poc/README.md#setup', file=sys.stderr)
        return 1
    finally:
        stop(owned_web)
        stop(owned_model)


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())

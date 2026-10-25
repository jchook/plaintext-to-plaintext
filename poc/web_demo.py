#!/usr/bin/env python3
"""Local, guided web demo for the existing opening-v1 codec."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import threading
import time
import urllib.request
import zlib

import opening
import p2p

ASSETS = Path(__file__).resolve().parent / 'web'
DEFAULT_OPENING = (ASSETS.parent.parent / 'experiments/003-opening-paragraph/openings/conference-followup.txt').read_text().strip()
MAX_MESSAGE_BYTES = 512
MAX_COVER_BYTES = 32768
MAX_REQUEST_BYTES = 65536
JOB_SECONDS = 1800
RESULT_SECONDS = 1800


def validate_request(body):
    if not isinstance(body, dict):
        raise ValueError('Expected a JSON object.')
    action = body.get('action')
    if action not in ('encode', 'decode'):
        raise ValueError('Choose encode or decode.')
    text = body.get('text')
    if not isinstance(text, str) or not text:
        raise ValueError('Enter a message.' if action == 'encode' else 'Paste the complete generated text.')
    data = text.encode('utf-8')
    limit = MAX_MESSAGE_BYTES if action == 'encode' else MAX_COVER_BYTES
    if len(data) > limit:
        raise ValueError(f'Input exceeds the demo limit of {limit:,} UTF-8 bytes.')
    key = body.get('key', '')
    if not isinstance(key, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', key):
        raise ValueError('The demo key must contain exactly 64 hexadecimal characters.')
    temperature = opening.validate_temperature(body.get('temperature', '1.2'))
    compression = body.get('compression', 'standard')
    if compression not in ('standard', 'raw', 'llm'):
        raise ValueError('Choose standard, raw, or model compression.')
    paragraph = (opening.validate_opening(body.get('opening', DEFAULT_OPENING))
                 if action == 'encode' else opening.split_cover(data)[0])
    return {'action': action, 'data': data, 'key': bytes.fromhex(key),
            'temperature': temperature, 'compression': compression, 'opening': paragraph}


class Demo:
    def __init__(self, model_url=p2p.DEFAULT_URL):
        self.model_url = model_url.rstrip('/')
        self.jobs = {}
        self.guard = threading.Lock()
        self.busy = threading.Lock()

    def status(self):
        try:
            with urllib.request.urlopen(self.model_url + '/props', timeout=3) as response:
                props = json.load(response)
            ready = (props.get('model_path', '').endswith(p2p.MODEL_SHA)
                     and props.get('total_slots') == 1)
            return {'ready': ready, 'message': 'Local model ready' if ready else 'Model configuration differs'}
        except (OSError, ValueError):
            return {'ready': False, 'message': 'Start the local model to generate text'}

    def start(self, request):
        if not self.busy.acquire(blocking=False):
            return None
        job_id = secrets.token_urlsafe(24)
        with self.guard:
            now = time.monotonic()
            self.jobs = {key: value for key, value in self.jobs.items()
                         if value['state'] == 'running' or now - value['updated'] < RESULT_SECONDS}
            if len(self.jobs) >= 20:
                oldest = min(self.jobs, key=lambda key: self.jobs[key]['updated'])
                del self.jobs[oldest]
            self.jobs[job_id] = {'state': 'running', 'phase': 'Preparing model', 'updated': now}
        thread = threading.Thread(target=self.run, args=(job_id, request), daemon=True)
        try:
            thread.start()
        except Exception:
            self.busy.release()
            raise
        return job_id

    def update(self, job_id, **values):
        with self.guard:
            self.jobs[job_id].update(values, updated=time.monotonic())

    def get(self, job_id):
        with self.guard:
            job = self.jobs.get(job_id)
            if job is None:
                return None
            if job['state'] != 'running' and time.monotonic() - job['updated'] >= RESULT_SECONDS:
                del self.jobs[job_id]
                return None
            return {key: value for key, value in job.items() if key != 'updated'}

    def run(self, job_id, request):
        started = time.monotonic()

        def progress(row):
            if time.monotonic() - started > JOB_SECONDS:
                raise p2p.CodecError('The demo reached its 30-minute processing limit. Try a shorter message.')
            self.update(job_id, progress=row)

        try:
            data, key = request['data'], request['key']
            temperature, paragraph = request['temperature'], request['opening']
            with p2p.server_lock(self.model_url):
                source = lambda: opening.SourceModel(self.model_url)
                oracle = opening.CoverModel(self.model_url, opening=paragraph, temperature=temperature)
                if request['action'] == 'encode':
                    mode = request['compression']
                    if mode == 'standard':
                        mode = 'zlib' if len(zlib.compress(data, level=9)) < len(data) else 'raw'
                    self.update(job_id, phase='Compressing and hiding your message')
                    cover, encoded = opening.encode(data, key, oracle, source, paragraph,
                                                    temperature, mode, progress=progress)
                    self.update(job_id, phase='Checking exact recovery', progress={})
                    decoder = opening.CoverModel(self.model_url, opening=paragraph, temperature=temperature)
                    recovered, decoded = opening.decode(cover, key, decoder, source, temperature, progress=progress)
                    if recovered != data or not decoded['authenticated']:
                        raise p2p.CodecError('The generated text failed its recovery check.')
                    result = {'text': cover.decode('utf-8'), 'recovered': recovered.decode('utf-8'),
                              'input_bytes': len(data), 'output_bytes': len(cover),
                              'compression': encoded['compression'], 'verified': True}
                else:
                    self.update(job_id, phase='Recovering and authenticating the message')
                    recovered, decoded = opening.decode(data, key, oracle, source, temperature, progress=progress)
                    result = {'text': recovered.decode('utf-8'), 'input_bytes': len(data),
                              'output_bytes': len(recovered), 'compression': decoded['compression'],
                              'authenticated': decoded['authenticated']}
                result['seconds'] = round(time.monotonic() - started, 1)
            self.update(job_id, state='complete', result=result, progress={})
        except (p2p.CodecError, ValueError, OSError) as error:
            self.update(job_id, state='failed', error=str(error), progress={})
        except Exception:
            self.update(job_id, state='failed', error='The demo could not finish this request. Check the model server.', progress={})
        finally:
            self.busy.release()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Do not log messages, keys, or job capability URLs.
        pass

    def reply(self, status, body, content_type='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'self'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def allowed_host(self):
        port = self.server.server_port
        return self.headers.get('Host') in (f'localhost:{port}', f'127.0.0.1:{port}')

    def do_GET(self):
        if not self.allowed_host():
            self.reply(403, {'error': 'Open this demo using its localhost address.'})
        elif self.path == '/api/config':
            self.reply(200, {'opening': DEFAULT_OPENING, 'temperature': '1.2',
                             'max_message_bytes': MAX_MESSAGE_BYTES, 'max_cover_bytes': MAX_COVER_BYTES,
                             'model': p2p.MODEL})
        elif self.path == '/api/status':
            self.reply(200, self.server.demo.status())
        elif self.path.startswith('/api/jobs/'):
            job = self.server.demo.get(self.path.removeprefix('/api/jobs/'))
            self.reply(200 if job else 404, job or {'error': 'This result expired. Run the demo again.'})
        elif self.path in ('/', '/app.js', '/style.css'):
            asset = ASSETS / {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}[self.path]
            content_type = {'/': 'text/html', '/app.js': 'text/javascript', '/style.css': 'text/css'}[self.path]
            self.reply(200, asset.read_bytes(), content_type + '; charset=utf-8')
        else:
            self.reply(404, {'error': 'Not found.'})

    def do_POST(self):
        if not self.allowed_host():
            self.reply(403, {'error': 'Invalid host.'})
            return
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers['Host']:
            self.reply(403, {'error': 'Open the demo in the same browser origin.'})
            return
        if self.path != '/api/jobs':
            self.reply(404, {'error': 'Not found.'})
            return
        if self.headers.get_content_type() != 'application/json':
            self.reply(415, {'error': 'Send JSON.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_REQUEST_BYTES:
                self.reply(413, {'error': 'The request exceeds the demo size limit.'})
                return
            request = validate_request(json.loads(self.rfile.read(length)))
        except (ValueError, p2p.CodecError, TypeError) as error:
            self.reply(400, {'error': str(error)})
            return
        job_id = self.server.demo.start(request)
        self.reply(202 if job_id else 409, {'id': job_id} if job_id else {'error': 'The model is busy. Wait for the current request to finish.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--url', default=p2p.DEFAULT_URL, help='Dedicated model server URL')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.demo = Demo(args.url)
    print(f'Web demo: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()

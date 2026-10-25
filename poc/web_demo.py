#!/usr/bin/env python3
"""Local, guided web demo for the existing opening-v1 codec."""
from __future__ import annotations

import argparse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import statistics
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
QUEUE_SECONDS = 1800
MAX_WAITING = 20


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
    def __init__(self, model_url=p2p.DEFAULT_URL, max_waiting=MAX_WAITING):
        if max_waiting < 1:
            raise ValueError('Queue size must be positive.')
        self.model_url = model_url.rstrip('/')
        self.jobs = {}
        self.guard = threading.Lock()
        self.pending = deque()
        self.active = None
        self.worker = None
        self.max_waiting = max_waiting
        self.durations = {'encode': deque(maxlen=20), 'decode': deque(maxlen=20)}

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
        job_id = secrets.token_urlsafe(24)
        with self.guard:
            now = time.monotonic()
            self.prune(now)
            if len(self.pending) >= self.max_waiting:
                return None
            self.jobs[job_id] = {'state': 'queued', 'phase': 'Waiting for the model',
                                 'created': now, 'updated': now, 'action': request['action'],
                                 'request': request}
            self.pending.append(job_id)
            if self.worker is None:
                self.worker = threading.Thread(target=self.work, daemon=True)
                try:
                    self.worker.start()
                except Exception:
                    self.worker = None
                    self.pending.remove(job_id)
                    del self.jobs[job_id]
                    raise
        return job_id

    def prune(self, now):
        """Called under guard; waiting payloads have a bounded lifetime."""
        for job_id in list(self.pending):
            job = self.jobs[job_id]
            if now - job['created'] >= QUEUE_SECONDS:
                self.pending.remove(job_id)
                job.pop('request', None)
                job.update(state='failed', error='Your place expired after 30 minutes in the queue. Please try again.', updated=now)
        finished = [(key, value) for key, value in self.jobs.items()
                    if value['state'] not in ('queued', 'running')]
        finished.sort(key=lambda pair: pair[1]['updated'], reverse=True)
        for index, (key, value) in enumerate(finished):
            if index >= 20 or now - value['updated'] >= RESULT_SECONDS:
                del self.jobs[key]

    def work(self):
        """One worker consumes a bounded FIFO, including verification."""
        while True:
            with self.guard:
                self.prune(time.monotonic())
                if not self.pending:
                    self.active = self.worker = None
                    return
                job_id = self.pending.popleft()
                job = self.jobs[job_id]
                request = job.pop('request')
                started = time.monotonic()
                job.update(state='running', phase='Preparing model', started=started, updated=started)
                self.active = job_id
            self.run(job_id, request)
            with self.guard:
                if self.jobs.get(job_id, {}).get('state') == 'complete':
                    self.durations[request['action']].append(time.monotonic() - started)
                self.active = None
            # Drop source bytes and key before waiting for another request.
            del request

    def estimate(self, action):
        samples = self.durations[action]
        return statistics.median(samples) if samples else None

    def cancel(self, job_id):
        with self.guard:
            self.prune(time.monotonic())
            job = self.jobs.get(job_id)
            if job is None:
                return 'missing'
            if job['state'] == 'cancelled':
                return 'cancelled'
            if job['state'] != 'queued':
                return 'started'
            self.pending.remove(job_id)
            job.pop('request', None)
            job.update(state='cancelled', phase='Removed from the queue', updated=time.monotonic())
            return 'cancelled'

    def update(self, job_id, **values):
        with self.guard:
            self.jobs[job_id].update(values, updated=time.monotonic())

    def get(self, job_id):
        with self.guard:
            now = time.monotonic()
            self.prune(now)
            job = self.jobs.get(job_id)
            if job is None:
                return None
            public = {key: job[key] for key in ('state', 'phase', 'progress', 'error', 'result') if key in job}
            if job['state'] == 'queued':
                position = self.pending.index(job_id)
                active = self.jobs.get(self.active)
                active = active if active and active['state'] == 'running' else None
                estimates = [self.estimate(self.jobs[key]['action']) for key in list(self.pending)[:position]]
                if active:
                    duration = self.estimate(active['action'])
                    estimates.append(None if duration is None else max(duration * .2, duration - (now - active['started'])))
                public.update(queue_position=position + 1, jobs_ahead=position + bool(active),
                              waiting_jobs=len(self.pending),
                              estimated_wait_seconds=None if None in estimates else round(sum(estimates)),
                              estimate_samples=sum(len(values) for values in self.durations.values()))
            elif job['state'] == 'running':
                duration = self.estimate(job['action'])
                public['taking_longer'] = duration is not None and now - job['started'] > duration
            return public

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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Do not log messages, keys, or job capability URLs.
        pass

    def reply(self, status, body, content_type='application/json; charset=utf-8', retry_after=None):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if retry_after is not None:
            self.send_header('Retry-After', str(retry_after))
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
        cancellation = re.fullmatch(r'/api/jobs/([A-Za-z0-9_-]+)/cancel', self.path)
        if self.path != '/api/jobs' and cancellation is None:
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
            body = json.loads(self.rfile.read(length))
            request = None if cancellation else validate_request(body)
        except (ValueError, p2p.CodecError, TypeError) as error:
            self.reply(400, {'error': str(error)})
            return
        if cancellation:
            outcome = self.server.demo.cancel(cancellation[1])
            status = {'cancelled': 200, 'missing': 404, 'started': 409}[outcome]
            self.reply(status, {'state': 'cancelled'} if outcome == 'cancelled' else
                       {'error': 'This job has already started. Please wait for the result.' if outcome == 'started' else 'This job expired.'})
            return
        job_id = self.server.demo.start(request)
        if job_id:
            self.reply(202, {'id': job_id})
        else:
            self.reply(429, {'error': 'The demo queue is full. Please try again in about a minute.'}, retry_after=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--url', default=p2p.DEFAULT_URL, help='Dedicated model server URL')
    parser.add_argument('--queue-size', type=int, default=MAX_WAITING, help='Maximum waiting jobs (default: 20)')
    args = parser.parse_args()
    if args.queue_size < 1:
        parser.error('--queue-size must be positive')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.demo = Demo(args.url, args.queue_size)
    print(f'Web demo: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()

"""Web boundary and authenticated jobs, using the real codec with test predictors."""
import contextlib
import http.client
import json
import threading
import time
import unittest
from unittest.mock import patch

import opening
import web_demo
from test_compact import SourceOracle
from test_p2p import Oracle


class DemoTests(unittest.TestCase):
    def request(self, **changes):
        body = {'action': 'encode', 'text': 'Café ☕\r\nKeep the whitespace. ',
                'opening': 'Thanks for meeting yesterday.', 'key': 'ab' * 32,
                'temperature': '1.2', 'compression': 'standard'}
        body.update(changes)
        return body

    def wait(self, demo, job_id):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            result = demo.get(job_id)
            if result['state'] not in ('queued', 'running'):
                return result
            time.sleep(.01)
        self.fail('Test job did not finish.')

    def test_invalid_requests_never_start_inference(self):
        cases = [None, [], self.request(action='delete'), self.request(key='abc'),
                 self.request(text=''), self.request(text='☕' * 180),
                 self.request(temperature='1.6'), self.request(opening='one\ntwo'),
                 self.request(compression='unknown'), self.request(action='decode', text='no opening'),
                 self.request(text='\ud800')]
        for body in cases:
            with self.subTest(body=repr(body)[:100]), self.assertRaises((ValueError, web_demo.p2p.CodecError)):
                web_demo.validate_request(body)

    def test_real_codec_jobs_verify_and_reject_wrong_key(self):
        demo = web_demo.Demo()
        with patch.object(opening, 'CoverModel', side_effect=lambda *a, **kw: Oracle()), \
             patch.object(opening, 'SourceModel', side_effect=lambda *a, **kw: SourceOracle()), \
             patch.object(web_demo.p2p, 'server_lock', side_effect=lambda *a: contextlib.nullcontext()):
            encoded = self.wait(demo, demo.start(web_demo.validate_request(self.request())))
            self.assertEqual(encoded['state'], 'complete', encoded)
            result = encoded['result']
            self.assertTrue(result['verified'])
            self.assertEqual(result['recovered'], self.request()['text'])
            self.assertTrue(result['text'].startswith(self.request()['opening'] + '\n\n'))
            decoded = self.wait(demo, demo.start(web_demo.validate_request(self.request(action='decode', text=result['text']))))
            self.assertEqual(decoded['result']['text'], self.request()['text'])
            self.assertTrue(decoded['result']['authenticated'])
            failed = self.wait(demo, demo.start(web_demo.validate_request(self.request(action='decode', text=result['text'], key='cd' * 32))))
            self.assertEqual(failed['state'], 'failed')
            self.assertNotIn('result', failed)

    def test_standard_compression_never_contacts_source_model(self):
        demo = web_demo.Demo()
        with patch.object(opening, 'CoverModel', side_effect=lambda *a, **kw: Oracle()), \
             patch.object(opening, 'SourceModel', side_effect=AssertionError('Source inference must be opt-in')), \
             patch.object(web_demo.p2p, 'server_lock', side_effect=lambda *a: contextlib.nullcontext()):
            for text, expected in [('short', 'raw'), ('repeat ' * 50, 'zlib')]:
                result = self.wait(demo, demo.start(web_demo.validate_request(self.request(text=text))))
                self.assertEqual(result['state'], 'complete', result)
                self.assertEqual(result['result']['compression'], expected)

    def test_mismatched_verification_does_not_release_cover(self):
        demo = web_demo.Demo()
        with patch.object(opening, 'CoverModel', return_value=Oracle()), \
             patch.object(opening, 'decode', return_value=(b'wrong', {'authenticated': True})), \
             patch.object(web_demo.p2p, 'server_lock', side_effect=lambda *a: contextlib.nullcontext()):
            result = self.wait(demo, demo.start(web_demo.validate_request(self.request())))
        self.assertEqual(result['state'], 'failed')
        self.assertNotIn('result', result)


class BlockingDemo(web_demo.Demo):
    """Hold the worker so admission, waiting, and races can be tested."""
    def __init__(self, max_waiting=2):
        super().__init__(max_waiting=max_waiting)
        self.started = threading.Event()
        self.release = threading.Event()
        self.order = []

    def run(self, job_id, request):
        self.order.append(job_id)
        self.started.set()
        if self.release.wait(10):
            self.update(job_id, state='complete', result={'text': request['data'].decode()})
        else:
            self.update(job_id, state='failed', error='Test worker timed out.')


class QueueTests(unittest.TestCase):
    request = DemoTests.request
    wait = DemoTests.wait
    def start_blocked(self, demo):
        first = demo.start(web_demo.validate_request(self.request()))
        self.assertTrue(demo.started.wait(2))
        self.addCleanup(demo.release.set)
        return first

    def test_fifo_positions_capacity_and_cancellation(self):
        demo = BlockingDemo()
        first = self.start_blocked(demo)
        second = demo.start(web_demo.validate_request(self.request()))
        third = demo.start(web_demo.validate_request(self.request()))
        self.assertEqual(demo.get(second)['queue_position'], 1)
        self.assertEqual(demo.get(third)['queue_position'], 2)
        self.assertEqual(demo.get(third)['jobs_ahead'], 2)
        self.assertIsNone(demo.get(third)['estimated_wait_seconds'])
        self.assertIsNone(demo.start(web_demo.validate_request(self.request())))
        self.assertEqual(demo.cancel(first), 'started')
        self.assertEqual(demo.cancel(second), 'cancelled')
        self.assertEqual(demo.cancel(second), 'cancelled')
        self.assertEqual(demo.get(third)['queue_position'], 1)
        fourth = demo.start(web_demo.validate_request(self.request()))
        self.assertIsNotNone(fourth)
        self.assertNotIn('request', demo.jobs[second])
        self.assertNotIn('request', demo.get(third))
        self.assertNotIn('key', demo.get(third))
        demo.release.set()
        self.assertEqual(self.wait(demo, fourth)['state'], 'complete')
        self.assertEqual(demo.order, [first, third, fourth])
        self.assertEqual(demo.get(second)['state'], 'cancelled')

    def test_eta_uses_remaining_work_and_distinct_action_samples(self):
        demo = BlockingDemo()
        first = self.start_blocked(demo)
        cover = 'Opening.\n\nSome generated prose.'
        second = demo.start(web_demo.validate_request(self.request(action='decode', text=cover)))
        third = demo.start(web_demo.validate_request(self.request()))
        with demo.guard:
            demo.durations['encode'].append(40)
            demo.durations['decode'].append(10)
            demo.jobs[first]['started'] = time.monotonic() - 10
        self.assertAlmostEqual(demo.get(second)['estimated_wait_seconds'], 30, delta=1)
        self.assertAlmostEqual(demo.get(third)['estimated_wait_seconds'], 40, delta=1)
        self.assertEqual(demo.get(third)['estimate_samples'], 2)

    def test_expiry_frees_waiting_payloads_and_results(self):
        demo = BlockingDemo(max_waiting=1)
        self.start_blocked(demo)
        waiting = demo.start(web_demo.validate_request(self.request()))
        with demo.guard:
            demo.jobs[waiting]['created'] = time.monotonic() - web_demo.QUEUE_SECONDS - 1
        self.assertEqual(demo.get(waiting)['state'], 'failed')
        self.assertNotIn('request', demo.jobs[waiting])
        self.assertIsNotNone(demo.start(web_demo.validate_request(self.request())))
        with demo.guard:
            demo.jobs[waiting]['updated'] = time.monotonic() - web_demo.RESULT_SECONDS - 1
        self.assertIsNone(demo.get(waiting))

    def test_concurrent_admission_is_bounded(self):
        demo = BlockingDemo(max_waiting=3)
        self.start_blocked(demo)
        admitted = []
        guard = threading.Lock()

        def submit():
            job_id = demo.start(web_demo.validate_request(self.request()))
            with guard:
                admitted.append(job_id)

        threads = [threading.Thread(target=submit) for _ in range(30)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(job is not None for job in admitted), 3)
        self.assertEqual(len(demo.pending), 3)
        self.assertEqual(len(demo.order), 1)

    def test_finished_retention_does_not_evict_waiting_jobs(self):
        demo = BlockingDemo(max_waiting=25)
        self.start_blocked(demo)
        waiting = [demo.start(web_demo.validate_request(self.request())) for _ in range(25)]
        self.assertTrue(all(waiting))
        with demo.guard:
            for index in range(25):
                demo.jobs[f'done-{index}'] = {'state': 'complete', 'updated': time.monotonic(), 'result': {}}
        self.assertEqual(demo.get(waiting[-1])['queue_position'], 25)
        self.assertEqual(sum(job['state'] == 'complete' for job in demo.jobs.values()), 20)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = web_demo.ThreadingHTTPServer(('127.0.0.1', 0), web_demo.Handler)
        cls.server.demo = web_demo.Demo()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def call(self, path='/', method='GET', body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_assets_config_and_missing_jobs(self):
        for path in ('/', '/app.js', '/style.css', '/api/config'):
            status, headers, body = self.call(path)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertTrue(body)
        self.assertEqual(self.call('/api/jobs/missing')[0], 404)
        self.assertEqual(self.call('/../web_demo.py')[0], 404)

    def test_reject_cross_origin_rebinding_and_bad_requests(self):
        body = json.dumps(DemoTests().request())
        self.assertEqual(self.call(headers={'Host': 'attacker.example'})[0], 403)
        headers = {'Content-Type': 'application/json', 'Origin': 'http://attacker.example'}
        self.assertEqual(self.call('/api/jobs', 'POST', body, headers)[0], 403)
        self.assertEqual(self.call('/api/jobs', 'POST', body, {'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.call('/api/jobs', 'POST', '[]', {'Content-Type': 'application/json'})[0], 400)
        self.assertEqual(self.call('/api/jobs', 'POST', 'x' * (web_demo.MAX_REQUEST_BYTES + 1), {'Content-Type': 'application/json'})[0], 413)

    def test_full_queue_retry_and_capability_cancellation(self):
        demo = BlockingDemo(max_waiting=1)
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(DemoTests().request())
        with patch.object(self.server, 'demo', demo):
            try:
                status, _, raw = self.call('/api/jobs', 'POST', body, headers)
                self.assertEqual(status, 202)
                first = json.loads(raw)['id']
                self.assertTrue(demo.started.wait(2))
                status, _, raw = self.call('/api/jobs', 'POST', body, headers)
                self.assertEqual(status, 202)
                waiting = json.loads(raw)['id']
                status, retry, _ = self.call('/api/jobs', 'POST', body, headers)
                self.assertEqual(status, 429)
                self.assertEqual(retry['Retry-After'], '60')
                self.assertEqual(self.call(f'/api/jobs/{first}/cancel', 'POST', '{}', headers)[0], 409)
                self.assertEqual(self.call('/api/jobs/missing/cancel', 'POST', '{}', headers)[0], 404)
                self.assertEqual(self.call(f'/api/jobs/{waiting}/cancel', 'POST', '{}', headers)[0], 200)
                self.assertEqual(json.loads(self.call(f'/api/jobs/{waiting}')[2])['state'], 'cancelled')
            finally:
                demo.release.set()


if __name__ == '__main__':
    unittest.main()

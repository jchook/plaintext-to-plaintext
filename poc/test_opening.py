"""Opening protocol invariants and adversarial inputs; no model or network."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.exceptions import InvalidTag

import opening
import p2p
from p2p import CodecError
from test_p2p import Oracle
from test_compact import SourceOracle


class OpeningTests(unittest.TestCase):
    paragraph = '  Café ☕: thanks for revising.  Let me know what you think. '.encode()
    material = b'opening experiment test key'

    def encode(self, data=b'Preserve this secret\r\n\t\x00', paragraph=None,
               temperature='1.0', **kwargs):
        return opening.encode(data, self.material, Oracle(), SourceOracle,
                              self.paragraph if paragraph is None else paragraph,
                              temperature=temperature, **kwargs)

    def decode(self, cover, material=None, temperature='1.0', **kwargs):
        return opening.decode(cover, self.material if material is None else material,
                              Oracle(), SourceOracle, temperature=temperature, **kwargs)

    def test_literal_template_rendering_and_exact_prefix(self):
        text = self.paragraph.decode()
        rendered = opening.render_prompt(self.paragraph)
        self.assertEqual(rendered.count(text), 1)
        self.assertNotIn('{{opening_paragraph}}', rendered)
        self.assertIn(opening.TEMPLATE.replace('{{opening_paragraph}}', text), rendered)
        cover, stats = self.encode()
        self.assertTrue(cover.startswith(self.paragraph + b'\n\n'))
        public, continuation = opening.split_cover(cover)
        self.assertEqual(public, self.paragraph)
        self.assertTrue(continuation)
        self.assertEqual(stats['cover_bytes'], len(cover))

    def test_fresh_roundtrips_without_sidecar_or_opening_parameter(self):
        for temperature in ('1.0', '1.2'):
            for mode in ('raw', 'zlib', 'llm', 'auto'):
                for data in (b'', b'The key is 12345', bytes(range(256))):
                    with self.subTest(temperature=temperature, mode=mode, size=len(data)):
                        cover, enc = self.encode(data, temperature=temperature, compression=mode)
                        recovered, dec = self.decode(cover, temperature=temperature)
                        self.assertEqual(recovered, data)
                        self.assertEqual(enc['payload_tokens'], dec['payload_tokens'])
                        self.assertTrue(dec['authenticated'])
                        cover.decode('utf-8')

    def test_opening_and_configuration_bound_to_keys(self):
        original = opening.keys(self.material, self.paragraph, '1.0')
        self.assertNotEqual(original, opening.keys(self.material, self.paragraph + b'!', '1.0'))
        self.assertNotEqual(original, opening.keys(self.material, self.paragraph, '1.2'))
        with patch.object(opening, 'TEMPLATE', opening.TEMPLATE + '\nA changed wrapper.'):
            self.assertNotEqual(original, opening.keys(self.material, self.paragraph, '1.0'))

    def test_frame_authentication_binds_opening_and_temperature(self):
        key, _ = opening.keys(self.material, self.paragraph)
        frame = opening.seal(b'\x00secret', key, self.paragraph)
        self.assertEqual(opening.unseal(frame, key, self.paragraph), b'\x00secret')
        for paragraph, temperature in ((self.paragraph + b'!', '1.0'),
                                       (self.paragraph, '1.2')):
            with self.subTest(temperature=temperature), self.assertRaises(InvalidTag):
                opening.unseal(frame, key, paragraph, temperature)

    def test_wrong_key_opening_temperature_and_template_fail(self):
        cover, _ = self.encode(compression='raw')
        variants = ((cover, b'wrong key', '1.0'),
                    (b'X' + cover[1:], self.material, '1.0'),
                    (cover, self.material, '1.2'))
        for changed, key, temperature in variants:
            with self.subTest(temperature=temperature, key=key), self.assertRaises(CodecError):
                self.decode(changed, key, temperature)
        with patch.object(opening, 'TEMPLATE', opening.TEMPLATE + '\nA changed wrapper.'):
            with self.assertRaises(CodecError):
                self.decode(cover)

    def test_modified_truncated_and_appended_continuations_fail(self):
        cover, _ = self.encode(compression='raw')
        public, continuation = opening.split_cover(cover)
        for changed in (b'!' + continuation[1:], continuation[:len(continuation) // 2],
                        continuation + b' extra', continuation[:-1]):
            with self.subTest(prefix=changed[:20]), self.assertRaises(CodecError):
                self.decode(public + b'\n\n' + changed)

    def test_invalid_openings_are_rejected(self):
        values = (b'', b'   ', b'one\ntwo', b'one\r\ntwo', b'one\rtwo', b'one\ttwo',
                  b'one\x00two', b'one\x1btwo', b'one\x7ftwo', b'\xff',
                  'one\u2028two', 'one\u2029two', 'one\u0085two', 'one\u200btwo',
                  b'<|eot_id|>', b'opening |> marker', b'{{opening_paragraph}}',
                  b'<opening_paragraph>', b'</opening_paragraph>',
                  b'x' * (opening.MAX_OPENING_BYTES + 1))
        for paragraph in values:
            with self.subTest(paragraph=repr(paragraph)[:70]), self.assertRaises(CodecError):
                opening.validate_opening(paragraph)

    def test_input_validation_precedes_source_or_cover_work(self):
        cover_oracle = Oracle()
        with patch.object(opening.source_codec, 'pack') as pack:
            with self.assertRaises(CodecError):
                opening.encode(b'secret', self.material, cover_oracle, SourceOracle,
                               b'invalid\nopening')
            pack.assert_not_called()
            self.assertEqual(cover_oracle.calls, 0)

    def test_only_registered_temperatures_are_accepted(self):
        for temperature in ('0', '1', '1.1', 'NaN', '-1', ''):
            with self.subTest(temperature=temperature), self.assertRaises(CodecError):
                self.encode(temperature=temperature)

    def test_invalid_cover_boundary_and_utf8_fail_before_prediction(self):
        for cover in (b'', b'no separator', b'opening\n\n', b'\n\ncontinuation',
                      b'one\ntwo\n\ncontinuation', b'one\r\n\r\ncontinuation',
                      b'\xff\n\ncontinuation'):
            oracle = Oracle()
            with self.subTest(cover=cover), self.assertRaises(CodecError):
                opening.decode(cover, self.material, oracle, SourceOracle)
            self.assertEqual(oracle.calls, 0)

    def test_empty_key_and_token_budget_fail(self):
        with self.assertRaises(CodecError):
            opening.keys(b'', self.paragraph)
        with self.assertRaises(CodecError):
            self.encode(max_tokens=1)


class OpeningCliTests(unittest.TestCase):
    def test_invalid_paths_and_openings_do_not_contact_model_or_write_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key, source, public = root / 'key', root / 'source', root / 'public'
            output, stats = root / 'output', root / 'stats'
            key.write_bytes(b'cli key')
            source.write_bytes(b'secret')
            public.write_bytes(b'Invalid\nopening')
            args = ['encode', '--key', str(key), '--input', str(source),
                    '--opening', str(public), '--output', str(output)]
            with patch.object(opening, 'CoverModel') as model, \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(opening.main(args), 1)
                self.assertFalse(output.exists())
                public.write_bytes(b'Thanks for revising the draft.')
                self.assertEqual(opening.main([*args, '--stats', str(output)]), 1)
                self.assertFalse(output.exists())
                stats.write_bytes(b'preserve existing stats')
                self.assertEqual(opening.main([*args, '--stats', str(stats)]), 1)
                self.assertFalse(output.exists())
                self.assertEqual(stats.read_bytes(), b'preserve existing stats')
                model.assert_not_called()

    def test_cli_fresh_decode_and_no_plaintext_for_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key, source, public = root / 'key', root / 'source', root / 'public'
            key.write_bytes(b'cli key')
            source.write_bytes(b'Exact secret\r\n\t\x00')
            public.write_bytes(b'Thanks for taking a look at the revised draft.')
            cover, output, stats = root / 'cover', root / 'output', root / 'stats'

            class StubCover(Oracle, opening.CoverModel):
                def __init__(self, url, cold, paragraph, temperature):
                    Oracle.__init__(self)
                    self.opening = paragraph
                    self.temperature_string = temperature
                    self.build = 'unit-test oracle'

            common = ['--key', str(key)]
            with patch.object(opening, 'CoverModel', StubCover), \
                    patch.object(opening, 'SourceModel', side_effect=lambda *a, **k: SourceOracle()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(opening.main(['encode', *common, '--opening', str(public),
                                              '--input', str(source), '--output', str(cover),
                                              '--stats', str(stats)]), 0)
                self.assertEqual(opening.main(['decode', *common, '--input', str(cover),
                                              '--output', str(output)]), 0)
                self.assertEqual(output.read_bytes(), source.read_bytes())
                before = output.read_bytes()
                self.assertEqual(opening.main(['decode', *common, '--input', str(cover),
                                              '--output', str(output)]), 1)
                self.assertEqual(output.read_bytes(), before)
                output.unlink()
                key.write_bytes(b'wrong key')
                self.assertEqual(opening.main(['decode', *common, '--input', str(cover),
                                              '--output', str(output)]), 1)
                self.assertFalse(output.exists())
                key.write_bytes(b'cli key')
                cover.write_bytes(b'X' + cover.read_bytes()[1:])
                self.assertEqual(opening.main(['decode', *common, '--input', str(cover),
                                              '--output', str(output)]), 1)
                self.assertFalse(output.exists())


class OpeningModelTests(unittest.TestCase):
    """Inspect actual model requests while replacing only HTTP transport."""
    paragraph = b'Thanks for looking at the revised draft.'

    def make_model(self, opening_tokens=8, left_tokens=20, right_tokens=10,
                   cold=False, truncated=False):
        requests = []
        paragraph = self.paragraph

        def request(model, path, body=None):
            requests.append((path, body))
            if path == '/props':
                return {'model_path': '/test/' + p2p.MODEL_SHA, 'total_slots': 1,
                        'build_info': 'unit-test transport'}
            if path == '/tokenize':
                if body['content'] == paragraph.decode():
                    count, start = opening_tokens, 1000
                elif body['content'].startswith(opening.CHAT_PREFIX):
                    count, start = left_tokens, 2000
                elif body['content'] == p2p.PROMPT:
                    count, start = 5, 3000
                else:
                    count, start = right_tokens, 4000
                return {'tokens': list(range(start, start + count))}
            if path == '/completion':
                return {'truncated': truncated, 'completion_probabilities': [{
                    'top_logprobs': [{'id': 1, 'bytes': list(b' one'), 'logprob': -1},
                                    {'id': 2, 'bytes': list(b' two'), 'logprob': -2}]}]}
            raise AssertionError('Unexpected endpoint ' + path)

        with patch.object(opening.CoverModel, 'request', request):
            model = opening.CoverModel(opening=paragraph, cold=cold)
        return model, request, requests

    def test_opening_tokenized_literally_and_prompt_history_bounded(self):
        model, request, requests = self.make_model()
        literal = [body for path, body in requests
                   if path == '/tokenize' and body['content'] == self.paragraph.decode()]
        self.assertEqual(len(literal), 1)
        self.assertIs(literal[0]['parse_special'], False)
        self.assertIs(literal[0]['add_special'], False)
        self.assertEqual(model.base[20:28], list(range(1000, 1008)))
        history = list(range(opening.HISTORY_TOKENS + 300))
        with patch.object(opening.CoverModel, 'request', request):
            model.rows(history)
            model.rows(history + [12345])
        calls = [body for path, body in requests if path == '/completion']
        self.assertFalse(calls[0]['cache_prompt'])
        self.assertTrue(calls[1]['cache_prompt'])
        self.assertEqual(calls[0]['prompt'], model.base + history[-opening.HISTORY_TOKENS:])
        self.assertLessEqual(len(calls[0]['prompt']) + calls[0]['n_predict'],
                             opening.CONTEXT_LIMIT)

    def test_cold_model_never_reuses_server_completion_cache(self):
        model, request, requests = self.make_model(cold=True)
        with patch.object(opening.CoverModel, 'request', request):
            model.rows([])
            model.rows([1])
        self.assertEqual([body['cache_prompt'] for path, body in requests
                          if path == '/completion'], [False, False])

    def test_opening_and_total_prompt_token_limits_before_scoring(self):
        self.make_model(opening_tokens=opening.MAX_OPENING_TOKENS)
        with self.assertRaisesRegex(CodecError, 'Opening exceeds'):
            self.make_model(opening_tokens=opening.MAX_OPENING_TOKENS + 1)
        self.make_model(opening_tokens=1, right_tokens=1,
                        left_tokens=opening.MAX_PROMPT_TOKENS - 2)
        with self.assertRaisesRegex(CodecError, 'context budget'):
            self.make_model(opening_tokens=1, right_tokens=1,
                            left_tokens=opening.MAX_PROMPT_TOKENS - 1)

    def test_server_truncation_and_history_policy_drift_fail(self):
        model, request, _ = self.make_model(truncated=True)
        with patch.object(opening.CoverModel, 'request', request):
            with self.assertRaisesRegex(CodecError, 'truncated'):
                model.rows([])
        with patch.object(p2p, 'CONTEXT_TOKENS', opening.HISTORY_TOKENS - 1):
            with self.assertRaisesRegex(CodecError, 'history policy'):
                self.make_model()


if __name__ == '__main__':
    unittest.main()

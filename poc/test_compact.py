"""Lossless source escapes, frame tampering, and fresh compact-codec decoders."""
import random
import unittest
from unittest.mock import patch
import zlib

from cryptography.exceptions import InvalidTag

import compact
from p2p import CodecError, Interval, TOTAL
import source_codec as source
from test_p2p import Oracle


class SourceOracle:
    """Byte vocabulary with only a few probable bytes exposed at each step."""
    def __init__(self):
        self.calls = 0

    def tokenize(self, data):
        return list(data)

    def detokenize(self, tokens):
        try:
            return bytes(tokens)
        except ValueError as error:
            raise CodecError('Invalid byte token.') from error

    def rows(self, history):
        self.calls += 1
        next_byte = ((history[-1] + 1) % 256) if history else 0
        ids = sorted({next_byte, 32, 101, 116})
        return [{'id': i, 'logprob': -1.8 - n * 0.2} for n, i in enumerate(ids)]


class CompactTests(unittest.TestCase):
    def test_source_exact_bytes_and_escape_paths(self):
        rng = random.Random(31)
        for data in (b'', b'The key is 12345', bytes(range(256)), rng.randbytes(333),
                     '  Café ☕\n你好\r\n\t\x00<|eot_id|>'.encode()):
            with self.subTest(size=len(data)):
                body, stats = source.compress_model(data, SourceOracle())
                self.assertEqual(source.decompress_model(body, SourceOracle()), data)
                if data.startswith(b'The'):
                    self.assertGreater(stats['escaped_source_tokens'], 0)

    def test_source_high_token_ids(self):
        class High(SourceOracle):
            def tokenize(self, data):
                return [65535, 65536, 128255]

            def detokenize(self, tokens):
                return b''.join(i.to_bytes(3, 'big') for i in tokens)

        data = High().detokenize([65535, 65536, 128255])
        body, _ = source.compress_model(data, High())
        self.assertEqual(source.decompress_model(body, High()), data)

    def test_digest_detects_wrong_restored_bytes(self):
        body, _ = source.compress_model(b'ABCD', SourceOracle())

        class Wrong(SourceOracle):
            def detokenize(self, tokens):
                return b'WXYZ'

        with self.assertRaisesRegex(CodecError, 'digest'):
            source.decompress_model(body, Wrong())

    def test_unsupported_tokenization_falls_back_without_loss(self):
        class Unsupported(SourceOracle):
            def tokenize(self, data):
                raise source.SourceUnsupported('Cannot represent these exact bytes.')

        packed, stats = source.pack(bytes(range(256)), 'auto', Unsupported)
        self.assertNotEqual(stats['compression'], 'llm')
        self.assertEqual(source.unpack(packed, Unsupported), bytes(range(256)))
        with self.assertRaises(source.SourceUnsupported):
            source.pack(b'abc', 'llm', Unsupported)

    def test_inexact_tokenizer_is_rejected(self):
        class Normalizing(SourceOracle):
            def tokenize(self, data):
                return list(data.strip())

        with self.assertRaises(source.SourceUnsupported):
            source.compress_model(b'  preserve spaces  ', Normalizing())

    def test_specific_server_parser_failure_allows_fallback(self):
        oracle = compact.SourceModel.__new__(compact.SourceModel)
        parser_error = CodecError('Inference HTTP 500: The model produced output that does not match '
                                  'the expected Content-only format')
        with patch.object(compact.Predictor, 'rows', side_effect=parser_error):
            with self.assertRaises(source.SourceUnsupported):
                oracle.rows([])
        connection_error = CodecError('Cannot reach inference server')
        with patch.object(compact.Predictor, 'rows', side_effect=connection_error):
            with self.assertRaises(CodecError) as caught:
                oracle.rows([])
            self.assertNotIsInstance(caught.exception, source.SourceUnsupported)

    def test_empty_compact_roundtrip(self):
        cover, stats = compact.encode(b'', b'key', Oracle(), SourceOracle)
        self.assertEqual(stats['frame_bytes'], 31)
        self.assertEqual(compact.decode(cover, b'key', Oracle(), SourceOracle)[0], b'')

    def test_raw_zlib_llm_auto_roundtrips(self):
        for mode in ('raw', 'zlib', 'llm', 'auto'):
            for data in (b'', b'ABCDEF', b'abcd ' * 40):
                with self.subTest(mode=mode, size=len(data)):
                    packed, _ = source.pack(data, mode, SourceOracle)
                    self.assertEqual(source.unpack(packed, SourceOracle), data)
        packed, stats = source.pack(b'x' * 1024, 'auto', SourceOracle)
        self.assertEqual(stats['compression'], 'zlib')

    def test_compact_frames_and_fresh_roundtrips(self):
        for mode in ('raw', 'zlib', 'llm', 'auto'):
            data = b'The key is 12345\r\n\t\x00'
            cover, enc = compact.encode(data, b'key', Oracle(), SourceOracle, compression=mode)
            recovered, dec = compact.decode(cover, b'key', Oracle(), SourceOracle)
            self.assertEqual(recovered, data)
            self.assertEqual(enc['payload_tokens'], dec['payload_tokens'])
            self.assertTrue(dec['authenticated'])

    def test_invalid_cover_and_wrong_key_fail(self):
        cover, _ = compact.encode(b'secret', b'key', Oracle(), SourceOracle, compression='raw')
        for changed, key in ((cover, b'wrong'), (b'!' + cover[1:], b'key'),
                             (cover[:len(cover) // 2], b'key'), (cover + b' extra', b'key')):
            with self.subTest(key=key, size=len(changed)), self.assertRaises(CodecError):
                compact.decode(changed, key, Oracle(), SourceOracle)

    def test_frame_authentication_includes_length(self):
        key, _ = compact.keys(b'key', 'warm')
        for size in (1, 15, 31, 32, 33, 100):
            data = bytes(range(size))
            frame = compact.seal(data, key, 'warm')
            self.assertEqual(len(frame), size + 30)
            self.assertEqual(compact.unseal(frame, key, 'warm'), data)
            for index in (0, 12, 13, 14, len(frame) - 1):
                changed = bytearray(frame)
                changed[index] ^= 1
                with self.assertRaises(InvalidTag):
                    compact.unseal(bytes(changed), key, 'warm')

    def test_bounded_malformed_decompression(self):
        invalid = (b'', b'\x03', b'\x01' + zlib.compress(b'ok') + b'extra',
                   b'\x01' + zlib.compress(b'x' * (source.MAX_SOURCE + 1)),
                   b'\x02' + b'\0' * 16 + source.varint(source.MAX_SOURCE + 1) + b'\0')
        for packed in invalid:
            with self.subTest(prefix=packed[:8]), self.assertRaises(CodecError):
                source.unpack(packed, SourceOracle)

    def test_positive_normalized_frequencies_and_interior_point(self):
        _, counts, ends = source.source_table([{'id': 42, 'logprob': -0.00000001}])
        self.assertTrue(all(x > 0 for x in counts))
        self.assertEqual(sum(counts), TOTAL)
        self.assertEqual(ends[-1], TOTAL)
        rng = random.Random(42)
        interval = Interval()
        for _ in range(100):
            start = rng.randrange(TOTAL - 1)
            interval.advance(start, rng.randrange(1, TOTAL - start + 1))
            coded = source.interior_point(interval)
            value, scale = int.from_bytes(coded, 'big'), 1 << (8 * len(coded))
            self.assertLess(interval.low * scale, value * interval.den)
            self.assertLess(value * interval.den, interval.high * scale)


if __name__ == '__main__':
    unittest.main()

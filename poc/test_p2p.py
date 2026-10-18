"""Codec invariants and adversarial cases; no model or network required."""
import decimal
import random
import unittest

from cryptography.exceptions import InvalidTag

from p2p import (Candidate, CodecError, Interval, TOTAL, candidates_from_response,
                 decode, derive_keys, encode, prefix_free, seal, table, unseal)


class Oracle:
    """Independent deterministic predictor with ambiguous raw candidate prefixes."""
    def __init__(self):
        self.calls = 0
        self.mass_sum = 0.0

    def candidates(self, history):
        self.calls += 1
        # The seed is reconstructed from the token history, not mutable state.
        seed = sum((i + 1) * token for i, token in enumerate(history[-13:]))
        rng = random.Random(seed)
        words = [b" the", b" there", b" friend", b" friends", b" walked", b" home", b"."]
        choices = [Candidate(i + 1, word, decimal.Decimal(rng.randrange(1, 100)))
                   for i, word in enumerate(words)]
        selected = prefix_free(choices)
        self.mass_sum += 1.0
        return selected


class CodecTests(unittest.TestCase):
    def test_exact_roundtrips_with_fresh_decoders(self):
        rng = random.Random(413)
        messages = [b"", b"The key is 12345", bytes(range(256)),
                    'Caf\u00e9 \u2615\n\u4f60\u597d\r\n\t\x00'.encode()]
        messages += [rng.randbytes(n) for n in (1, 7, 31, 32, 33, 63, 64, 65, 127)]
        for message in messages:
            with self.subTest(size=len(message)):
                cover, enc = encode(message, b"test key", Oracle())
                recovered, dec = decode(cover, b"test key", Oracle())
                self.assertEqual(message, recovered)
                self.assertEqual(enc['payload_tokens'], dec['payload_tokens'])
                self.assertTrue(dec['authenticated'])
                cover.decode('utf-8')

    def test_wrong_key_rejected(self):
        cover, _ = encode(b"do not return unauthenticated bytes", b"right", Oracle())
        with self.assertRaises(CodecError):
            decode(cover, b"wrong", Oracle())

    def test_modified_truncated_and_extra_text_rejected(self):
        cover, _ = encode(b"important punctuation\r\n\t", b"key", Oracle())
        variants = [b"!" + cover[1:], cover[:len(cover) // 2], cover + b" extra", b""]
        for changed in variants:
            with self.subTest(cover=changed[:20]), self.assertRaises(CodecError):
                decode(changed, b"key", Oracle())

    def test_new_nonce_produces_distinct_covers(self):
        a, _ = encode(b"same message", b"key", Oracle())
        b, _ = encode(b"same message", b"key", Oracle())
        self.assertNotEqual(a, b)
        self.assertEqual(decode(a, b"key", Oracle())[0], b"same message")
        self.assertEqual(decode(b, b"key", Oracle())[0], b"same message")

    def test_authenticated_frame_boundaries(self):
        key, _ = derive_keys(b"key material")
        for size in range(100):
            data = bytes(range(size))
            frame = seal(data, key)
            self.assertEqual(len(frame) % 32, 0)
            self.assertEqual(unseal(frame, key), data)
            with self.assertRaises(InvalidTag):
                unseal(frame[:-1] + bytes([frame[-1] ^ 1]), key)

    def test_prefix_free_selection_and_byte_filters(self):
        rows = [
            {'id': 1, 'bytes': list(b' the'), 'logprob': -1.0},
            {'id': 2, 'bytes': list(b' there'), 'logprob': -1.1},
            {'id': 3, 'bytes': list(b' then'), 'logprob': -1.2},
            {'id': 4, 'bytes': list(b' friend'), 'logprob': -2.0},
            {'id': 5, 'bytes': [0xff], 'logprob': -0.1},
            {'id': 6, 'bytes': list(b'<|eot_id|>'), 'logprob': -0.1},
            {'id': 7, 'logprob': -0.1},
        ]
        choices = candidates_from_response(rows)
        self.assertGreaterEqual(len(choices), 2)
        for a in choices:
            for b in choices:
                if a != b:
                    self.assertFalse(a.raw.startswith(b.raw))
        self.assertNotIn(5, [c.token_id for c in choices])
        self.assertNotIn(6, [c.token_id for c in choices])

    def test_table_is_positive_exact_and_keyed(self):
        choices = Oracle().candidates([])
        a, ends = table(choices, b"a", [])
        b, _ = table(choices, b"b", [])
        self.assertEqual(sum(count for _, count in a), TOTAL)
        self.assertTrue(all(count > 0 for _, count in a))
        self.assertEqual(ends[-1], TOTAL)
        self.assertEqual(sorted(count for _, count in a), sorted(count for _, count in b))

    def test_half_open_interval_boundary(self):
        interval = Interval()
        self.assertEqual(interval.choose(1, 2, [TOTAL // 2, TOTAL]), 1)
        interval.advance(TOTAL // 2, TOTAL // 2)
        self.assertIsNone(interval.common_bytes(1))
        interval.advance(0, TOTAL // 128)
        self.assertEqual(interval.common_bytes(1), b'\x80')

    def test_failure_has_bounded_work(self):
        with self.assertRaises(CodecError):
            encode(b"cannot fit in one token", b"key", Oracle(), max_tokens=1)


if __name__ == '__main__':
    unittest.main()

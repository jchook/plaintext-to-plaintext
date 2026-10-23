#!/usr/bin/env python3
"""Compact v2 experiment: lossless source coding, encryption, and prose coding."""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import hmac
import json
import math
from pathlib import Path
import secrets
import struct
import sys
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

import p2p
import source_codec

VARIED_PROMPT = (
    "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
    "Write natural, concrete prose. Output only the prose, without a title or introduction."
    "<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
    "Write a notebook of observations from an unfamiliar town. Move freely between "
    "people, shops, food, objects, overheard conversations, small mishaps, local history, "
    "and plans for tomorrow. Invent specific names, places, colors, quantities, and details. "
    "Vary the subjects and sentence openings. Use ordinary paragraphs. Write about 1500 words."
    "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
)
# Named profiles are part of the shared protocol, not per-message metadata.
PROFILES = {
    'journal': (p2p.PROMPT, 64, '1.0'),
    'varied': (VARIED_PROMPT, 64, '1.0'),
    'warm': (VARIED_PROMPT, 64, '1.2'),
}
MAX_FRAME = 65536
FRAME_OVERHEAD = 30  # Two length bytes, a 12-byte nonce, and a 16-byte tag.


def protocol(profile):
    prompt, n_probs, temperature = PROFILES[profile]
    config = json.dumps([prompt, n_probs, temperature], ensure_ascii=True).encode()
    return b'plaintext-to-plaintext-compact-v2/' + p2p.MODEL_SHA.encode() + b'/' + hashlib.sha256(config).digest()


def keys(material, profile):
    if not material:
        raise p2p.CodecError("The key file is empty.")
    value = HKDF(algorithm=hashes.SHA256(), length=64, salt=protocol(profile),
                 info=b'encryption-and-interval-order').derive(material)
    return value[:32], value[32:]


def seal(packed, key, profile):
    if not 1 <= len(packed) <= MAX_FRAME - FRAME_OVERHEAD:
        raise p2p.CodecError("Compressed source exceeds the frame limit.")
    nonce = secrets.token_bytes(12)
    header = mask_length(struct.pack('>H', len(packed)), key, nonce)
    return nonce + header + ChaCha20Poly1305(key).encrypt(nonce, packed, protocol(profile) + header)


def mask_length(header, key, nonce):
    header_key = hmac.digest(key, b'compact-v2 length-mask key', 'sha256')
    mask = hmac.digest(header_key, nonce, 'sha256')[:2]
    return bytes(a ^ b for a, b in zip(header, mask))


def unseal(frame, key, profile):
    if len(frame) < FRAME_OVERHEAD + 1:
        raise InvalidTag
    size = struct.unpack('>H', mask_length(frame[12:14], key, frame[:12]))[0]
    if len(frame) != size + FRAME_OVERHEAD:
        raise InvalidTag
    return ChaCha20Poly1305(key).decrypt(frame[:12], frame[14:], protocol(profile) + frame[12:14])


class Predictor(p2p.Llama):
    def __init__(self, url=p2p.DEFAULT_URL, cold=False, prompt=p2p.PROMPT, n_probs=64):
        super().__init__(url, cold)
        if prompt != p2p.PROMPT:
            self.base = self.request('/tokenize', {'content': prompt, 'add_special': False,
                                                  'parse_special': True})['tokens']
        self.n_probs = n_probs

    def rows(self, history):
        use_cache = bool(self.calls) and not self.cold
        self.calls += 1
        response = self.request('/completion', {
            'prompt': self.base + history[-p2p.CONTEXT_TOKENS:],
            'n_predict': 1, 'n_probs': self.n_probs, 'temperature': -1, 'seed': 42,
            'stream': False, 'cache_prompt': use_cache,
            'return_tokens': True, 'top_k': 0, 'top_p': 1.0, 'min_p': 0.0, 'repeat_penalty': 1.0,
        })
        if response.get('truncated'):
            raise p2p.CodecError("Inference server truncated the shared context.")
        records = response.get('completion_probabilities') or response.get('probs')
        if not records:
            raise p2p.CodecError("Inference server did not return token probabilities.")
        return records[0]['top_logprobs']


class SourceModel(Predictor):
    def __init__(self, url=p2p.DEFAULT_URL, cold=False):
        super().__init__(url, cold, '<|begin_of_text|>', 64)

    def tokenize(self, data):
        try:
            text = data.decode('utf-8', errors='strict')
        except UnicodeDecodeError as error:
            raise source_codec.SourceUnsupported("Non-UTF-8 source uses raw or DEFLATE coding.") from error
        return self.request('/tokenize', {'content': text, 'add_special': False,
                                          'parse_special': False})['tokens']

    def detokenize(self, tokens):
        return self.request('/detokenize', {'tokens': tokens})['content'].encode('utf-8')

    def rows(self, history):
        try:
            return super().rows(history)
        except p2p.CodecError as error:
            # This server build can reject a one-token completion at a source
            # prefix (for example, partway through a Unicode sequence). Treat
            # that exact parser error as an unavailable compression candidate.
            # Connection failures and other inference errors remain fatal.
            if ('Inference HTTP 500:' in str(error) and
                    'does not match the expected Content-only format' in str(error)):
                raise source_codec.SourceUnsupported(
                    'The local server could not score this source prefix; raw or DEFLATE is available.') from error
            raise


class CoverModel(Predictor):
    def __init__(self, url=p2p.DEFAULT_URL, cold=False, profile='warm'):
        prompt, n_probs, temperature = PROFILES[profile]
        super().__init__(url, cold, prompt, n_probs)
        self.temperature = Decimal(temperature)
        self.top_mass_sum = 0.0
        self.top_entropy_sum = 0.0
        self.selected_entropy_sum = 0.0

    def candidates(self, history):
        rows = self.rows(history)
        with localcontext() as ctx:
            ctx.prec = 40
            original = {int(row['id']): Decimal(str(row['logprob'])).exp() for row in rows
                        if Decimal(str(row['logprob'])).is_finite()}
            self.top_mass_sum += float(sum(original.values()))
            adjusted = [dict(row, logprob=str(Decimal(str(row['logprob'])) / self.temperature))
                        for row in rows]
            selected = p2p.candidates_from_response(adjusted)
            self.mass_sum += float(sum(original[c.token_id] for c in selected))
            weights = [w ** (Decimal(1) / self.temperature) for w in original.values()]
            self.top_entropy_sum += entropy([float(w / sum(weights)) for w in weights])
            mass = sum(c.weight for c in selected)
            self.selected_entropy_sum += entropy([float(c.weight / mass) for c in selected])
        return selected


def entropy(probabilities):
    return -sum(p * math.log2(p) for p in probabilities if p)


def encode_frame(frame, order_key, oracle, max_tokens=5000, progress=None):
    num = ((int.from_bytes(frame, 'big') << 128) | secrets.randbits(128)) * 2 + 1
    den = 1 << (len(frame) * 8 + 129)
    interval, history, parts = p2p.Interval(), [], []
    entropy_sum, expected_bytes_sum = 0.0, 0.0
    for count in range(1, max_tokens + 1):
        entries, ends = p2p.table(oracle.candidates(history), order_key, history)
        entropy_sum += entropy([frequency / p2p.TOTAL for _, frequency in entries])
        expected_bytes_sum += sum(len(item.raw) * frequency / p2p.TOTAL for item, frequency in entries)
        index = interval.choose(num, den, ends)
        choice, frequency = entries[index]
        interval.advance(0 if index == 0 else ends[index - 1], frequency)
        history.append(choice.token_id)
        parts.append(choice.raw)
        p2p.report(progress, count, interval, len(frame) * 8)
        if interval.common_bytes(len(frame)) == frame:
            cover = b''.join(parts)
            payload_bytes = len(cover)
            payload_tokens = len(history)
            diagnostics = {
                'average_top_probability_mass': getattr(oracle, 'top_mass_sum', 0) / count,
                'average_retained_probability_mass': oracle.mass_sum / count,
                'average_top_entropy_bits': getattr(oracle, 'top_entropy_sum', 0) / count,
                'average_selected_entropy_bits': getattr(oracle, 'selected_entropy_sum', 0) / count,
            }
            cover += p2p.finish(oracle, history, cover)
            return cover, {
                **diagnostics, 'frame_bytes': len(frame), 'cover_bytes': len(cover),
                'payload_cover_bytes': payload_bytes, 'suffix_bytes': len(cover) - payload_bytes,
                'payload_tokens': payload_tokens, 'total_tokens': len(history),
                'cover_model_calls': oracle.calls,
                'average_table_entropy_bits': entropy_sum / count,
                'realized_frame_bits_per_token': 8 * len(frame) / count,
                'realized_frame_bits_per_cover_byte': 8 * len(frame) / len(cover),
                'expected_entropy_bits_per_byte': entropy_sum / expected_bytes_sum,
                'interval_information_bits': interval.information_bits(),
            }
    raise p2p.CodecError(f"Encoding exceeded {max_tokens} tokens; no cover file was written.")


def decode_frame(cover, encryption_key, order_key, oracle, profile, max_tokens=5000, progress=None):
    interval, history, offset, frame_size = p2p.Interval(), [], 0, None
    for count in range(1, max_tokens + 1):
        if offset >= len(cover):
            break
        entries, ends = p2p.table(oracle.candidates(history), order_key, history)
        matches = [i for i, (item, _) in enumerate(entries) if cover.startswith(item.raw, offset)]
        if len(matches) != 1:
            raise p2p.CodecError(f"Cover differs from the shared model at byte {offset}.")
        index = matches[0]
        choice, frequency = entries[index]
        interval.advance(0 if index == 0 else ends[index - 1], frequency)
        offset += len(choice.raw)
        history.append(choice.token_id)
        p2p.report(progress, count, interval)
        if frame_size is None:
            header = interval.common_bytes(14)
            if header is not None:
                length = mask_length(header[12:14], encryption_key, header[:12])
                frame_size = struct.unpack('>H', length)[0] + FRAME_OVERHEAD
                if not FRAME_OVERHEAD < frame_size <= MAX_FRAME:
                    raise p2p.CodecError("Invalid frame length: wrong key or changed cover.")
        frame = interval.common_bytes(frame_size) if frame_size else None
        if frame is not None:
            try:
                packed = unseal(frame, encryption_key, profile)
            except InvalidTag as error:
                raise p2p.CodecError("Frame authentication failed.") from error
            payload_tokens = len(history)
            if cover[offset:] != p2p.finish(oracle, history, cover[:offset]):
                raise p2p.CodecError("Cover has an altered, missing, or extra sentence-completion suffix.")
            return packed, {'frame_bytes': frame_size, 'cover_bytes': len(cover),
                            'payload_tokens': payload_tokens, 'total_tokens': len(history),
                            'cover_model_calls': oracle.calls, 'authenticated': True}
    raise p2p.CodecError("No authenticated message recovered within the available cover and token limit.")


def encode(data, material, cover_oracle, source_factory, profile='warm', compression='auto',
           max_tokens=5000, progress=None):
    started = time.monotonic()
    encryption_key, order_key = keys(material, profile)
    packed, source_stats = source_codec.pack(data, compression, source_factory, progress)
    compressed_at = time.monotonic()
    frame = seal(packed, encryption_key, profile)
    cover, stats = encode_frame(frame, order_key, cover_oracle, max_tokens, progress)
    stats.update(source_stats)
    stats.update({'plaintext_bytes': len(data), 'profile': profile, 'protocol': 'compact-v2',
                  'compression_seconds': round(compressed_at - started, 3),
                  'elapsed_seconds': round(time.monotonic() - started, 3)})
    return cover, stats


def decode(cover, material, cover_oracle, source_factory, profile='warm', max_tokens=5000, progress=None):
    started = time.monotonic()
    encryption_key, order_key = keys(material, profile)
    packed, stats = decode_frame(cover, encryption_key, order_key, cover_oracle, profile, max_tokens, progress)
    decompressed_at = time.monotonic()
    data = source_codec.unpack(packed, source_factory, progress)
    stats.update({'plaintext_bytes': len(data), 'profile': profile, 'protocol': 'compact-v2',
                  'compression': {0: 'raw', 1: 'zlib', 2: 'llm'}[packed[0]],
                  'decompression_seconds': round(time.monotonic() - decompressed_at, 3),
                  'elapsed_seconds': round(time.monotonic() - started, 3)})
    return data, stats


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('encode', 'decode'))
    parser.add_argument('--url', default=p2p.DEFAULT_URL)
    parser.add_argument('--cold', action='store_true')
    parser.add_argument('--profile', choices=PROFILES, default='warm')
    parser.add_argument('--compression', choices=('auto', 'raw', 'zlib', 'llm'), default='auto')
    parser.add_argument('--key', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--stats')
    parser.add_argument('--max-tokens', type=int, default=5000)
    args = parser.parse_args(argv)
    try:
        if Path(args.output).exists() or (args.stats and Path(args.stats).exists()):
            raise p2p.CodecError("Output or statistics file already exists; choose a new path.")
        data, material = Path(args.input).read_bytes(), Path(args.key).read_bytes()
        with p2p.server_lock(args.url):
            oracle = CoverModel(args.url, args.cold, args.profile)
            source_factory = lambda: SourceModel(args.url, args.cold)
            progress = lambda row: print(json.dumps(row), file=sys.stderr, flush=True)
            if args.command == 'encode':
                output, stats = encode(data, material, oracle, source_factory, args.profile,
                                       args.compression, args.max_tokens, progress)
            else:
                output, stats = decode(data, material, oracle, source_factory, args.profile,
                                       args.max_tokens, progress)
            stats.update({'model': p2p.MODEL, 'model_sha256': p2p.MODEL_SHA,
                          'server_build': oracle.build, 'cold': args.cold,
                          'key_sha256': hashlib.sha256(material).hexdigest()})
            p2p.write_new(args.output, output)
            if args.stats:
                p2p.write_new(args.stats, (json.dumps(stats, indent=2) + '\n').encode())
            print(json.dumps(stats, indent=2), file=sys.stderr)
        return 0
    except (p2p.CodecError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

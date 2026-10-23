#!/usr/bin/env python3
"""Opening v1: a public first paragraph steers an authenticated prose cover.

The decoder requires the cover, key, shared template/model, and temperature. It
extracts the public paragraph from the cover; no per-message sidecar is needed.
Existing compact v2 profiles and their wire formats are unchanged.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import secrets
import struct
import sys
import time

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

import compact
import p2p
import source_codec

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / 'experiments/003-opening-paragraph/prompt-template-v1.txt'
TEMPLATE = TEMPLATE_PATH.read_bytes().decode('utf-8')
TEMPLATE_VERSION = 'opening-template-v1'
SLOT = '{{opening_paragraph}}'
TEMPERATURES = ('1.0', '1.2')
MAX_OPENING_BYTES = 4096
MAX_OPENING_TOKENS = 256
MAX_PROMPT_TOKENS = 768
CONTEXT_LIMIT = 2048
HISTORY_TOKENS = 1024
N_PROBS = 64
CHAT_PREFIX = (
    '<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n'
    'Write natural, concrete prose. Output only the prose, without a title or introduction.'
    '<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n'
)
CHAT_SUFFIX = '<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n'
SourceModel = compact.SourceModel


def validate_opening(opening):
    if isinstance(opening, str):
        try:
            opening = opening.encode('utf-8', errors='strict')
        except UnicodeEncodeError as error:
            raise p2p.CodecError('Opening must be valid UTF-8.') from error
    if not isinstance(opening, bytes):
        raise p2p.CodecError('Opening must be UTF-8 bytes or text.')
    if not opening or len(opening) > MAX_OPENING_BYTES:
        raise p2p.CodecError(f'Opening must contain 1–{MAX_OPENING_BYTES} UTF-8 bytes.')
    try:
        text = opening.decode('utf-8', errors='strict')
    except UnicodeDecodeError as error:
        raise p2p.CodecError('Opening must be valid UTF-8.') from error
    if not text.strip() or any(not ch.isprintable() for ch in text):
        raise p2p.CodecError('Opening must be one nonempty printable paragraph without line breaks or controls.')
    if any(marker in text for marker in ('<|', '|>', SLOT, '<opening_paragraph', '</opening_paragraph')):
        raise p2p.CodecError('Opening contains a reserved template delimiter or model control marker.')
    return opening


def validate_temperature(temperature):
    if temperature not in TEMPERATURES:
        raise p2p.CodecError('Temperature must be exactly 1.0 or 1.2.')
    return temperature


def template_parts():
    if TEMPLATE.count(SLOT) != 1:
        raise p2p.CodecError('Shared prompt template must contain exactly one opening slot.')
    return TEMPLATE.split(SLOT)


def render_prompt(opening):
    opening = validate_opening(opening)
    before, after = template_parts()
    return CHAT_PREFIX + before + opening.decode('utf-8') + after + CHAT_SUFFIX


def split_cover(cover):
    if not isinstance(cover, bytes):
        raise p2p.CodecError('Cover must be bytes.')
    opening, separator, continuation = cover.partition(b'\n\n')
    if not separator or not continuation:
        raise p2p.CodecError('Cover requires an opening, exactly two separator newlines, and a continuation.')
    return validate_opening(opening), continuation


def config(opening, temperature='1.0'):
    opening = validate_opening(opening)
    validate_temperature(temperature)
    prompt = render_prompt(opening)
    return {
        'protocol': 'opening-v1', 'model_sha256': p2p.MODEL_SHA,
        'template_version': TEMPLATE_VERSION,
        'template_sha256': hashlib.sha256(TEMPLATE.encode('utf-8')).hexdigest(),
        'rendered_prompt_sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
        'opening_sha256': hashlib.sha256(opening).hexdigest(),
        'temperature': temperature, 'n_probs': N_PROBS,
        'context_limit': CONTEXT_LIMIT, 'history_tokens': HISTORY_TOKENS,
        'max_opening_tokens': MAX_OPENING_TOKENS, 'max_prompt_tokens': MAX_PROMPT_TOKENS,
        'tokenization': 'template-segments-special/opening-literal-v1',
        'candidate_rules': 'compact-v2-prefix-free',
        'completion_rule': 'p2p-v1-sentence-finish',
        'source_coding': 'compact-v2-auto-independent-model',
    }


def protocol(opening, temperature='1.0'):
    encoded = json.dumps(config(opening, temperature), sort_keys=True, separators=(',', ':')).encode('utf-8')
    return b'plaintext-to-plaintext-opening-v1/' + hashlib.sha256(encoded).digest()


def keys(material, opening, temperature='1.0'):
    if not material:
        raise p2p.CodecError('The key file is empty.')
    value = HKDF(algorithm=hashes.SHA256(), length=64, salt=protocol(opening, temperature),
                 info=b'encryption-and-interval-order').derive(material)
    return value[:32], value[32:]


def seal(packed, key, opening, temperature='1.0'):
    if not 1 <= len(packed) <= compact.MAX_FRAME - compact.FRAME_OVERHEAD:
        raise p2p.CodecError('Compressed source exceeds the frame limit.')
    nonce = secrets.token_bytes(12)
    header = compact.mask_length(struct.pack('>H', len(packed)), key, nonce)
    return nonce + header + ChaCha20Poly1305(key).encrypt(nonce, packed, protocol(opening, temperature) + header)


def unseal(frame, key, opening, temperature='1.0'):
    if len(frame) < compact.FRAME_OVERHEAD + 1:
        raise InvalidTag
    size = struct.unpack('>H', compact.mask_length(frame[12:14], key, frame[:12]))[0]
    if len(frame) != size + compact.FRAME_OVERHEAD:
        raise InvalidTag
    return ChaCha20Poly1305(key).decrypt(frame[:12], frame[14:], protocol(opening, temperature) + frame[12:14])


class CoverModel(compact.CoverModel):
    """Reuse v2 scoring, with explicit configuration instead of global profiles."""
    def __init__(self, url=p2p.DEFAULT_URL, cold=False, opening=b'', temperature='1.0'):
        self.opening = validate_opening(opening)
        self.temperature_string = validate_temperature(temperature)
        before, after = template_parts()
        # Llama initializes/checks the pinned server and starts with no cached
        # completion calls. All three tokenization requests remain read-only.
        p2p.Llama.__init__(self, url, cold)
        opening_tokens = self.request('/tokenize', {
            'content': self.opening.decode('utf-8'), 'add_special': False,
            'parse_special': False})['tokens']
        if len(opening_tokens) > MAX_OPENING_TOKENS:
            raise p2p.CodecError(f'Opening exceeds {MAX_OPENING_TOKENS} model tokens.')
        left = self.request('/tokenize', {'content': CHAT_PREFIX + before,
                                         'add_special': False, 'parse_special': True})['tokens']
        right = self.request('/tokenize', {'content': after + CHAT_SUFFIX,
                                          'add_special': False, 'parse_special': True})['tokens']
        self.base = left + opening_tokens + right
        if len(self.base) > MAX_PROMPT_TOKENS or len(self.base) + HISTORY_TOKENS + 1 > CONTEXT_LIMIT:
            raise p2p.CodecError('Rendered prompt exceeds the fixed context budget.')
        self.opening_tokens = len(opening_tokens)
        self.n_probs = N_PROBS
        self.temperature = Decimal(temperature)
        self.top_mass_sum = self.top_entropy_sum = self.selected_entropy_sum = 0.0
        # Predictor.rows uses p2p.CONTEXT_TOKENS; reject drift in this shared dependency.
        if p2p.CONTEXT_TOKENS != HISTORY_TOKENS:
            raise p2p.CodecError('Shared rolling history policy differs from opening v1.')


def decode_frame(cover, encryption_key, order_key, oracle, opening, temperature='1.0',
                 max_tokens=5000, progress=None):
    # The arithmetic and suffix rules match v2. Keep the authentication boundary
    # here explicit so opening-v1 never mutates the existing protocol registry.
    interval, history, offset, frame_size = p2p.Interval(), [], 0, None
    for count in range(1, max_tokens + 1):
        if offset >= len(cover):
            break
        entries, ends = p2p.table(oracle.candidates(history), order_key, history)
        matches = [i for i, (item, _) in enumerate(entries) if cover.startswith(item.raw, offset)]
        if len(matches) != 1:
            raise p2p.CodecError(f'Cover differs from the shared model at continuation byte {offset}.')
        index = matches[0]
        choice, frequency = entries[index]
        interval.advance(0 if index == 0 else ends[index - 1], frequency)
        offset += len(choice.raw)
        history.append(choice.token_id)
        p2p.report(progress, count, interval)
        if frame_size is None:
            header = interval.common_bytes(14)
            if header is not None:
                length = compact.mask_length(header[12:14], encryption_key, header[:12])
                frame_size = struct.unpack('>H', length)[0] + compact.FRAME_OVERHEAD
                if not compact.FRAME_OVERHEAD < frame_size <= compact.MAX_FRAME:
                    raise p2p.CodecError('Invalid frame length: wrong key, opening, configuration, or cover.')
        frame = interval.common_bytes(frame_size) if frame_size else None
        if frame is not None:
            try:
                packed = unseal(frame, encryption_key, opening, temperature)
            except InvalidTag as error:
                raise p2p.CodecError('Frame authentication failed.') from error
            payload_tokens = len(history)
            if cover[offset:] != p2p.finish(oracle, history, cover[:offset]):
                raise p2p.CodecError('Cover has an altered, missing, or extra sentence-completion suffix.')
            return packed, {'frame_bytes': frame_size, 'cover_bytes': len(cover),
                            'payload_tokens': payload_tokens, 'total_tokens': len(history),
                            'cover_model_calls': oracle.calls, 'authenticated': True}
    raise p2p.CodecError('No authenticated message recovered within the available cover and token limit.')


def public_stats(opening, temperature, continuation, oracle):
    prompt = render_prompt(opening)
    result = config(opening, temperature)
    result.update({
        'opening': opening.decode('utf-8'), 'rendered_prompt': prompt,
        'opening_bytes': len(opening), 'separator_bytes': 2,
        'continuation_bytes': len(continuation),
        'full_cover_bytes': len(opening) + 2 + len(continuation),
        'cover_bytes': len(opening) + 2 + len(continuation),
    })
    if hasattr(oracle, 'opening_tokens'):
        result['opening_tokens'] = oracle.opening_tokens
        result['fixed_prompt_tokens'] = len(oracle.base)
        result['fixed_prompt_token_sha256'] = hashlib.sha256(
            json.dumps(oracle.base, separators=(',', ':')).encode()).hexdigest()
    return result


def check_oracle(oracle, opening, temperature):
    # Toy oracles can exercise framing without inference; real predictors must
    # match the authenticated context exactly.
    if (getattr(oracle, 'opening', opening) != opening or
            getattr(oracle, 'temperature_string', temperature) != temperature):
        raise p2p.CodecError('Cover model does not match the opening and temperature.')


def encode(data, material, cover_oracle, source_factory, opening, temperature='1.0',
           compression='auto', max_tokens=5000, progress=None):
    started = time.monotonic()
    opening = validate_opening(opening)
    check_oracle(cover_oracle, opening, temperature)
    encryption_key, order_key = keys(material, opening, temperature)
    packed, source_stats = source_codec.pack(data, compression, source_factory, progress)
    compressed_at = time.monotonic()
    frame = seal(packed, encryption_key, opening, temperature)
    continuation, stats = compact.encode_frame(frame, order_key, cover_oracle, max_tokens, progress)
    stats.update(source_stats)
    stats.update(public_stats(opening, temperature, continuation, cover_oracle))
    stats.update({'plaintext_bytes': len(data), 'compression_seconds': round(compressed_at - started, 3),
                  'elapsed_seconds': round(time.monotonic() - started, 3),
                  'realized_frame_bits_per_continuation_byte': 8 * len(frame) / len(continuation),
                  'realized_frame_bits_per_cover_byte': 8 * len(frame) / stats['full_cover_bytes'],
                  'realized_frame_bits_per_full_cover_byte': 8 * len(frame) / stats['full_cover_bytes']})
    return opening + b'\n\n' + continuation, stats


def decode(cover, material, cover_oracle, source_factory, temperature='1.0', max_tokens=5000, progress=None):
    started = time.monotonic()
    opening, continuation = split_cover(cover)
    check_oracle(cover_oracle, opening, temperature)
    encryption_key, order_key = keys(material, opening, temperature)
    packed, stats = decode_frame(continuation, encryption_key, order_key, cover_oracle,
                                 opening, temperature, max_tokens, progress)
    decompressed_at = time.monotonic()
    data = source_codec.unpack(packed, source_factory, progress)
    stats.update(public_stats(opening, temperature, continuation, cover_oracle))
    stats.update({'plaintext_bytes': len(data), 'compression': {0: 'raw', 1: 'zlib', 2: 'llm'}[packed[0]],
                  'decompression_seconds': round(time.monotonic() - decompressed_at, 3),
                  'elapsed_seconds': round(time.monotonic() - started, 3)})
    return data, stats


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('encode', 'decode'))
    parser.add_argument('--url', default=p2p.DEFAULT_URL)
    parser.add_argument('--cold', action='store_true')
    parser.add_argument('--opening', help='UTF-8 paragraph file; required for encoding only')
    parser.add_argument('--temperature', choices=TEMPERATURES, default='1.0')
    parser.add_argument('--compression', choices=('auto', 'raw', 'zlib', 'llm'), default='auto')
    parser.add_argument('--key', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--stats')
    parser.add_argument('--max-tokens', type=int, default=5000)
    args = parser.parse_args(argv)
    try:
        if args.max_tokens <= 0:
            raise p2p.CodecError('Token limit must be positive.')
        if Path(args.output).exists() or (args.stats and Path(args.stats).exists()):
            raise p2p.CodecError('Output or statistics file already exists; choose a new path.')
        if args.stats and Path(args.output).resolve() == Path(args.stats).resolve():
            raise p2p.CodecError('Output and statistics require distinct paths.')
        data, material = Path(args.input).read_bytes(), Path(args.key).read_bytes()
        if not material:
            raise p2p.CodecError('The key file is empty.')
        if args.command == 'encode':
            if not args.opening:
                raise p2p.CodecError('Encoding requires --opening.')
            opening = validate_opening(Path(args.opening).read_bytes())
        else:
            if args.opening:
                raise p2p.CodecError('Decode reads the opening from the cover; omit --opening.')
            opening, _ = split_cover(data)
        with p2p.server_lock(args.url):
            oracle = CoverModel(args.url, args.cold, opening, args.temperature)
            source_factory = lambda: SourceModel(args.url, args.cold)
            progress = lambda row: print(json.dumps(row), file=sys.stderr, flush=True)
            if args.command == 'encode':
                output, stats = encode(data, material, oracle, source_factory, opening,
                                       args.temperature, args.compression, args.max_tokens, progress)
            else:
                output, stats = decode(data, material, oracle, source_factory, args.temperature,
                                       args.max_tokens, progress)
            stats.update({'model': p2p.MODEL, 'server_build': oracle.build, 'cold': args.cold,
                          'key_sha256': hashlib.sha256(material).hexdigest()})
            p2p.write_new(args.output, output)
            if args.stats:
                p2p.write_new(args.stats, (json.dumps(stats, indent=2) + '\n').encode())
            print(json.dumps(stats, indent=2), file=sys.stderr)
        return 0
    except (p2p.CodecError, OSError, ValueError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Lossless source coding with top-token probabilities and an escape alphabet."""
from __future__ import annotations

from decimal import Decimal, localcontext
import hashlib
import hmac
import math
import zlib

from p2p import CodecError, Interval, TOTAL

MAX_SOURCE = 65505
MAX_SOURCE_TOKENS = 8192
VOCAB_SIZE = 128256  # Pinned Llama 3.2 vocabulary, including special tokens.
ESCAPE = -1


class SourceUnsupported(CodecError):
    """Input is still representable by the raw or DEFLATE source codec."""


def frequencies(weights):
    """Positive integer counts, in the supplied order; stable remainder ties."""
    if not weights or len(weights) > TOTAL:
        raise CodecError("Invalid probability alphabet.")
    with localcontext() as ctx:
        ctx.prec = 40
        if any(not w.is_finite() or w <= 0 for w in weights):
            raise CodecError("Invalid probability weight.")
        mass = sum(weights)
        exact = [w * (TOTAL - len(weights)) / mass for w in weights]
        counts = [1 + int(x) for x in exact]
        order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - int(exact[i])), i))
        for i in order[:TOTAL - sum(counts)]:
            counts[i] += 1
    ends, end = [], 0
    for count in counts:
        end += count
        ends.append(end)
    return counts, ends


def source_table(rows):
    """Keep token IDs, including nonprintable pieces; reserve residual mass for escape."""
    with localcontext() as ctx:
        ctx.prec = 40
        weights = {}
        for row in rows:
            token = int(row['id'])
            logp = Decimal(str(row['logprob']))
            if not 0 <= token < VOCAB_SIZE or not logp.is_finite():
                continue
            weights[token] = logp.exp()
        if not weights:
            raise CodecError("Source predictor returned no valid probabilities.")
        residual = max(Decimal(1) - sum(weights.values()), Decimal(1) / TOTAL)
        ids = sorted(weights) + [ESCAPE]
        counts, ends = frequencies([weights[i] for i in ids[:-1]] + [residual])
    return ids, counts, ends


def varint(value):
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def read_varint(data, offset=0):
    start, value = offset, 0
    for shift in range(0, 28, 7):
        if offset >= len(data):
            break
        part = data[offset]
        offset += 1
        value |= (part & 127) << shift
        if part < 128:
            if data[start:offset] != varint(value):
                break
            return value, offset
    raise CodecError("Invalid source-code length.")


def interior_point(interval):
    """Canonical whole-byte rational strictly inside the final coding interval."""
    size = max(1, math.floor(interval.information_bits() / 8))
    while True:
        scale = 1 << (size * 8)
        value = interval.low * scale // interval.den + 1
        if value * interval.den < interval.high * scale:
            return value.to_bytes(size, 'big')
        size += 1


def compress_model(data, oracle, progress=None):
    tokens = oracle.tokenize(data)
    if len(tokens) > MAX_SOURCE_TOKENS:
        raise SourceUnsupported("Source exceeds the model-codec token limit.")
    if any(not 0 <= token < VOCAB_SIZE for token in tokens):
        raise SourceUnsupported("Source tokenizer returned an unsupported token ID.")
    if oracle.detokenize(tokens) != data:
        raise SourceUnsupported("Tokenizer does not reproduce the original bytes.")
    interval, history, escapes = Interval(), [], 0
    for step, token in enumerate(tokens, 1):
        ids, counts, ends = source_table(oracle.rows(history))
        index = ids.index(token) if token in ids else len(ids) - 1
        interval.advance(0 if index == 0 else ends[index - 1], counts[index])
        if ids[index] == ESCAPE:
            escapes += 1
            # Uniform 17-bit token ID: one binary decision, then 16 literal bits.
            interval.advance((token >> 16) * (TOTAL // 2), TOTAL // 2)
            interval.advance(token & 65535, 1)
        history.append(token)
        if progress and (step == 1 or step % 100 == 0):
            progress({'phase': 'compress', 'source_tokens': step, 'total_source_tokens': len(tokens)})
    coded = interior_point(interval) if tokens else b''
    # Authenticate the exact restored bytes too: a mismatched inference runtime
    # must not silently turn authenticated compressed data into another message.
    body = hashlib.sha256(data).digest()[:16] + varint(len(data)) + varint(len(tokens)) + coded
    return body, {'source_tokens': len(tokens), 'escaped_source_tokens': escapes,
                  'source_information_bits': interval.information_bits()}


def decompress_model(body, oracle, progress=None):
    if len(body) < 18:
        raise CodecError("Truncated model-compressed source.")
    digest = body[:16]
    byte_count, offset = read_varint(body, 16)
    token_count, offset = read_varint(body, offset)
    if byte_count > MAX_SOURCE or token_count > MAX_SOURCE_TOKENS:
        raise CodecError("Model-compressed source exceeds the protocol limit.")
    coded = body[offset:]
    if not token_count:
        if byte_count or coded or digest != hashlib.sha256(b'').digest()[:16]:
            raise CodecError("Invalid empty source representation.")
        return b''
    if not coded:
        raise CodecError("Missing source arithmetic code.")
    num, den = int.from_bytes(coded, 'big'), 1 << (len(coded) * 8)
    interval, history = Interval(), []
    for step in range(1, token_count + 1):
        ids, counts, ends = source_table(oracle.rows(history))
        index = interval.choose(num, den, ends)
        token = ids[index]
        interval.advance(0 if index == 0 else ends[index - 1], counts[index])
        if token == ESCAPE:
            high = interval.choose(num, den, [TOTAL // 2, TOTAL])
            interval.advance(high * (TOTAL // 2), TOTAL // 2)
            low = ((num * interval.den - interval.low * den) * TOTAL
                   // ((interval.high - interval.low) * den))
            if not 0 <= low < TOTAL:
                raise CodecError("Invalid escaped source token.")
            interval.advance(low, 1)
            token = high * TOTAL + low
            if token >= VOCAB_SIZE:
                raise CodecError("Escaped source token is outside the vocabulary.")
        history.append(token)
        if progress and (step == 1 or step % 100 == 0):
            progress({'phase': 'decompress', 'source_tokens': step, 'total_source_tokens': token_count})
    if interior_point(interval) != coded:
        raise CodecError("Noncanonical source arithmetic code; inference may differ.")
    data = oracle.detokenize(history)
    if len(data) != byte_count:
        raise CodecError("Recovered source length differs; inference may differ.")
    if not hmac.compare_digest(hashlib.sha256(data).digest()[:16], digest):
        raise CodecError("Recovered source digest differs; inference may differ.")
    return data


def pack(data, mode, oracle_factory, progress=None):
    if len(data) > MAX_SOURCE:
        raise CodecError(f"Source exceeds {MAX_SOURCE} bytes.")
    choices = {'raw': b'\x00' + data}
    stats = {}
    if mode in ('auto', 'zlib'):
        choices['zlib'] = b'\x01' + zlib.compress(data, level=9)
    if mode in ('auto', 'llm'):
        oracle = oracle_factory()
        try:
            body, stats = compress_model(data, oracle, progress)
            choices['llm'] = b'\x02' + body
        except SourceUnsupported as error:
            if mode == 'llm':
                raise
            stats['llm_skipped'] = str(error)
        stats['source_model_calls'] = oracle.calls
    # Insertion order prefers raw, then DEFLATE, when sizes tie: no need to
    # require model inference during restoration unless it saves bytes.
    selected = min(choices, key=lambda name: len(choices[name])) if mode == 'auto' else mode
    stats.update({'compression': selected, 'source_candidate_bytes': {k: len(v) for k, v in choices.items()},
                  'packed_source_bytes': len(choices[selected])})
    return choices[selected], stats


def unpack(packed, oracle_factory, progress=None):
    if not packed:
        raise CodecError("Missing source-code type.")
    kind, body = packed[0], packed[1:]
    if kind == 0:
        data = body
    elif kind == 1:
        decoder = zlib.decompressobj()
        try:
            data = decoder.decompress(body, MAX_SOURCE + 1)
        except zlib.error as error:
            raise CodecError("Invalid DEFLATE source.") from error
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise CodecError("Truncated, oversized, or trailing DEFLATE source.")
    elif kind == 2:
        data = decompress_model(body, oracle_factory(), progress)
    else:
        raise CodecError("Unknown source-code type.")
    if len(data) > MAX_SOURCE:
        raise CodecError("Recovered source exceeds the protocol limit.")
    return data

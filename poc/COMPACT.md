# Compact codec experiment

See [the measured results and saved cover texts](COMPACT_RESULTS.md) for the local
comparison, including the observed prose-quality tradeoffs.

`compact.py` is a separate v2 protocol. The original `p2p.py` and its saved covers
remain unchanged. V2 tries three lossless source representations, encrypts the
smallest one, and encodes the resulting frame into model-generated prose.

## Run

Use the same dedicated server as the original POC:

```sh
python3 poc/p2p.py serve
```

In another terminal:

```sh
python3 poc/compact.py encode --key poc/keys/alice.txt --input message.txt --output cover.txt --stats encode.json
python3 poc/compact.py decode --key poc/keys/alice.txt --input cover.txt --output recovered.txt --stats decode.json
cmp message.txt recovered.txt
```

The decoder receives only the exact cover, key file, and agreed protocol/profile.
It does not read the encoder's statistics or token trace. The default profile is
`warm`; choose the same `--profile` on both sides. The compression type is inside
the authenticated frame, so the decoder does not need that setting.

## Source compression

Automatic mode compares three complete representations, including their headers:

| Representation | How it preserves the source |
| --- | --- |
| Raw | A type byte followed by the original bytes. |
| DEFLATE | A type byte followed by a standard zlib stream. |
| LLM | A type byte, a 16-byte source digest, source/token counts, and an arithmetic code. |

For LLM compression, the tokenizer must reproduce the input bytes exactly. Each
source token is encoded according to the model's next-token probabilities,
conditioned on the source prefix. The top 64 tokens get individual intervals; an
escape interval gets the remaining probability mass. An escaped token is followed
by its exact 17-bit vocabulary ID. No prediction needs to be correct: unlikely
tokens simply cost more bits. Token IDs are reconstructed before detokenizing, so
partial UTF-8 pieces are supported here.

The compression model starts with the beginning-of-text token and keeps the last
1024 source tokens. It evaluates the actual source prefix; it is not asked to
generate, summarize, or agree with the message. **Unlike the original POC, this
optional pass sends the original text to the local model.** The cover-generation
pass still sees only its fixed prompt and its own previously emitted tokens.

After reconstructing the source, the decoder checks its SHA-256 digest truncated
to 128 bits. That digest is inside the authenticated ciphertext. This additional
check prevents an incompatible source predictor from silently restoring different
bytes. It also costs 16 bytes, which can outweigh compression gains on tiny inputs.
Non-UTF-8 inputs, inexact tokenization, and sources over 8192 tokens are excluded
from the LLM candidate in automatic mode. This server build also rejected a
one-token scoring request within the Unicode test source with a content-parser
error. That specific error makes the LLM candidate unavailable; raw and DEFLATE
remain available. Other inference errors still stop the operation. The fallback
reason is recorded in the encoder statistics.

`--compression raw`, `zlib`, or `llm` forces a representation for experiments;
`auto` chooses the smallest. The source limit is 65505 bytes, and an oversized
forced compressed representation can still exceed the frame limit.

## Framing and cover generation

V2 removes the old 32-byte padding boundary and four-byte inner length. Its frame
contains a 12-byte random nonce, two masked length bytes, the encrypted packed
source, and a 16-byte ChaCha20-Poly1305 tag. Total framing overhead is 30 bytes,
plus the source representation. For raw source, that means 31 bytes overhead.

The length mask is HMAC-SHA256 under a separate domain-derived subkey, using the
nonce as input. It prevents a small, predictable length from becoming a fixed
prefix of the arithmetic input. The masked length is included in AEAD associated
data. The decoder recovers the first 14 frame bytes, unmasks the length, then
recovers and authenticates exactly that many frame bytes. Plaintext is written
only after authentication, suffix checking, and source restoration succeed.

All profiles use the existing exact-integer arithmetic coder and prefix-free
printable token selection:

| Profile | Cover prompt | Temperature |
| --- | --- | --- |
| `journal` | Original pleasant-day journal | 1.0 |
| `varied` | Town observations with varied subjects and specific details | 1.0 |
| `warm` | Same town-observation prompt | 1.2 |

Temperature is applied locally to the top-64 model probabilities, before
prefix-free selection. The server request itself remains deterministic. The
prompt, temperature, and candidate count are bound into key derivation and frame
authentication. Changing profiles changes the protocol.

The encoder records probability mass before and after filtering, entropy before
and after prefix-free selection, entropy after integer quantization, realized
frame bits per token, frame bits per visible byte, and sentence-ending overhead.
These quantities separate source compression, cover capacity, and coding losses.
The top-64 entropy is conditional on that subset; it is not full-vocabulary entropy.

The model, runtime, cache-reset sequence, context policy, and exact text must still
match. This experiment establishes neither cross-device portability nor statistical
invisibility. A warmer distribution may shorten the text while making individual
phrases less natural. The default still emits a deterministic sentence completion,
which can add substantial overhead to a short message.

## Reproduce measurements

```sh
python3 -m unittest discover -s poc -p 'test_*.py' -v
python3 poc/compact_demo.py --repetitions 2
python3 poc/compact_demo.py --cases belfry --variants legacy journal-raw varied-raw warm-raw warm-auto --repetitions 2
```

Each run creates a new directory containing original inputs, cover texts, restored
bytes, per-process statistics, and `results.json` with exact-byte comparisons and
SHA-256 hashes. Random nonces produce different cover lengths on repeated runs;
small sample counts should not be treated as a stable benchmark.

# Plaintext-to-plaintext proof of concept

For the source-compression and shorter-frame experiment, see
[the compact v2 codec](COMPACT.md). The commands below retain the original v1
protocol and remain compatible with its saved examples.

This standalone prototype encrypts arbitrary input bytes and turns the encrypted
frame into natural-language cover text using the downloaded Llama 3.2 3B model.
Decoding reconstructs the frame and authenticates it before writing the recovered
bytes. The original message is never sent to the model.

The decoder needs the cover text, the exact key file, this protocol implementation,
and the pinned model/runtime. It does not use an encoder trace, stored probability
tables, statistics files, or a per-message sidecar.

## Run

Python 3.10+ and `cryptography` are required. From the project root:

```sh
python3 -m pip install -r poc/requirements.txt
ollama pull llama3.2:3b-instruct-q4_K_M
python3 poc/p2p.py serve
```

Keep that terminal open. In another terminal:

```sh
python3 poc/p2p.py probe
python3 poc/p2p.py encode --key poc/keys/alice.txt --input poc/examples/key-message.txt --output /tmp/message.cover.txt
python3 poc/p2p.py decode --key poc/keys/alice.txt --input /tmp/message.cover.txt --output /tmp/message.recovered.txt
cmp poc/examples/key-message.txt /tmp/message.recovered.txt
```

Outputs must not already exist. Input and recovered files are read and written as
bytes, preserving Unicode, tabs, line endings, and empty input. Copy the cover
exactly; do not add a newline or reformat it.

`serve` runs Ollama's bundled `llama-server` on loopback port 11535, independently
of the normal Ollama service. It uses the existing GGUF rather than downloading
another model. Set `P2P_LLAMA_SERVER` if the executable lives elsewhere, and
`OLLAMA_MODELS` if your model store is not `~/.ollama/models`. On systems whose
Ollama installation does not bundle this executable, provide a compatible
llama.cpp server; replay and model-identity checks must pass. Stop it with Ctrl-C.

The pinned GGUF SHA-256 is
`dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff`.
The validated server build is recorded in the example statistics. Merely using
the same model name does not establish compatibility across different runtimes.

## Demonstrations and checks

```sh
python3 -m unittest discover -s poc -p 'test_*.py' -v
python3 poc/demo.py
```

The demo runs each encoder and decoder in separate processes, compares exact
bytes and SHA-256 hashes, and saves the cover texts and measurements in a new
`poc/runs/` directory. Its inputs include the key message, the belfry warning,
Unicode with mixed whitespace, and an empty file. `--cases belfry unicode`
selects a smaller run.

## Mechanism

1. HKDF-SHA256 derives independent encryption and interval-ordering keys from the
   complete key file. ChaCha20-Poly1305 encrypts a length-prefixed, padded payload
   with a fresh random nonce. The encrypted frame occupies a multiple of 32 bytes.
2. The fixed prompt asks Llama to write an ordinary journal entry. The codec uses
   its next-token probabilities, filtering the top 64 candidates to printable,
   valid UTF-8 pieces. A maximum-weight prefix-free selection makes emitted
   pieces unambiguous when the decoder reads their visible bytes.
3. Positive integer frequencies totaling 65536 define exact rational intervals.
   A keyed permutation orders those intervals. A random interior point in the
   encrypted frame's binary interval selects successive model tokens.
4. The decoder reconstructs those intervals. It tries authenticated frames at
   32-byte boundaries; the valid authentication tag establishes the frame length.
   A deterministic sentence-completion suffix is also reproduced and checked.

The mathematical interval operations are exact Python integer operations. The
interior point includes a finite 128-bit random tail: recovery is exact, while
distribution matching is an approximation. Filtering, probability rounding,
finite padding, and the stopping rule also change the unrestricted model's
output distribution. This prototype does not establish statistical invisibility.

## Inference state

Ollama's regular API reused cached prefixes in ways that changed probabilities.
This prototype controls a dedicated single-slot llama.cpp session instead. Each
operation clears its cache with the first inference request, then follows the
same sequence of token-ID requests on both sides. The codec serializes its own
clients with a local lock. Do not send unrelated inference requests to that
server during an operation.

The server uses four CPU threads, no GPU offload, and a fixed 2048-token context.
The protocol keeps the fixed prompt plus the last 1024 emitted tokens. `probe`
compares two independently reset inference sequences. `--cold` recomputes every
prompt instead of reusing the cache; both sides must use the same setting.

This establishes a tested local implementation, not bitwise portability to every
CPU, GPU, quantization, or library version. Phone performance has not been tested.
Encoding is currently verbose and performs one inference request per cover token.
There is a 5000-token work limit by default and a 65536-byte encrypted-frame limit.
Failures never return unauthenticated plaintext.

## Demo key

`keys/alice.txt` is the complete Project Gutenberg text of Lewis Carroll's
*Alice's Adventures in Wonderland*, downloaded from
<https://www.gutenberg.org/cache/epub/11/pg11.txt>.
The file retains the source's license and attribution.

Its SHA-256 is
`01b38ea4c710a84bc18d0bd41271a5a1a92b94e97b2812f4dece97d4a694725e`.
It is a public demonstration key: anyone with the same book file can decode these
examples. The implementation also accepts an arbitrary private key file.

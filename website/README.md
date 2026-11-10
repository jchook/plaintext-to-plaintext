# Recorded-example playground

This is a static website. Visitors can replay 24 real archived round trips,
change between recorded inputs, cover styles, temperatures and trials, and reveal
the saved recovery. The interface explicitly identifies playback and saved
recovery. It does not encode new messages, decrypt covers in the browser, call
an LLM, collect hardware information, or send slider values to a server.

All example inputs and generated outputs come from the public
`experiments/003-opening-paragraph/runs/pilot-20261021` archive. The exporter
checks exact recovered bytes, the recorded authentication result, opening bytes,
and cover lengths before writing the dataset. Every recording links to its
encoder metadata on GitHub. No private keys or model files are included.

From the repository root:

```sh
python3 scripts/export_examples.py
python3 -m http.server 8002 --bind 127.0.0.1 --directory website/dist
```

Open **http://127.0.0.1:8002**. To check that the exported data matches the archive:

```sh
python3 scripts/export_examples.py --check
node --check website/dist/app.js
```

The `dist/` directory is the complete deployment output. It can be hosted as
ordinary static files on a CDN, a static hosting service, or a web server. No
frontend dependency installation, model server, database, or server-side Python
process is needed for the hosted website. Node is only used for the optional
JavaScript syntax check above.

The hardware guide is deliberately conservative. It suggests the existing CPU
profile when total system RAM is at least 8 GB, a planning allowance rather than
a measured minimum. It does not add dedicated GPU VRAM to CPU RAM or double-count
Apple unified memory. The current codec has not validated GPU replay or smaller
models, so those choices do not silently select another model or runtime.

Model download sizes are reference values checked on October 27, 2026:
[Llama 3.2 1B](https://ollama.com/library/llama3.2:1b) is about 1.3 GB, and
[Qwen3 0.6B](https://ollama.com/library/qwen3:0.6b) is about 523 MB. These are
candidate models, not supported codec profiles. The verified 3B download command
uses the explicit `llama3.2:3b-instruct-q4_K_M` tag; the local launcher checks the
expected GGUF SHA-256 before starting a model it owns.

For live inference, use `./run-local.sh` from the repository root and follow
the [local setup guide](../poc/README.md#setup). The capability requirements for
future provider adapters are repeatable candidate probabilities, exact token IDs
and bytes, token-history control, reversible tokenization, explicit model/profile
identity, and fresh encode/decode checks. Ollama's current generation API exposes
[log probabilities](https://docs.ollama.com/api/generate), but direct API support
still needs a codec adapter and exact recovery validation.

## Sampler illustration

The “How it works” section uses an independent toy arithmetic coder in
`dist/sampler.js`. Enter 1–16 bytes of example ciphertext in hexadecimal and step through candidate
selection, or use Play/Pause to watch the output develop. The default contains
eight bytes. We use exact integer arithmetic so the longer examples do not lose
precision as the interval narrows.
Decode the emitted tokens to see the recoverable bit prefix grow. Change the
opening context to select a different invented vocabulary and interval order.
These are illustrative token strings and probabilities, not model measurements.
The toy uses small dyadic weights and fixed context-specific toy keys; the codec
uses its own candidate filtering, integer probability table, and HMAC ordering.

The opening paragraph is public context included in the cover. In opening-v1,
we bind it into both prompt rendering and key derivation. Keep the cryptographic
key secret. Use the CLI to embed ciphertext from age, GPG, or another tool;
`--compression raw` avoids compression of already encrypted data. The codec
still applies its own authenticated encryption.

Check all 256 single-byte values in both toy contexts, plus longer payloads up
to sixteen bytes, partial decoding, and wrong-context rejection:

```sh
node website/test-sampler.cjs
```

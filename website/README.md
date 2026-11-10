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

## Recorded sampler walkthrough

The “How it works” section replays two real opening-v1 experiment covers.
`dist/sampler-recordings.json` includes each retained token candidate, its
integer coding probability, the actual selection, and the recovered ciphertext.
We record the probability tables while decoding the archived covers through the
pinned model. We verify authenticated recovery and exact sentence completion
before exporting. No secret key material is included in the website.

Use Play/Pause, Next, Back, and Reset to inspect the recording. The browser
reconstructs the arithmetic intervals and ciphertext bits from the recorded
tables. The ciphertext is read-only because a different payload would require
new model inference. The final sentence completion does not encode more data.
The table shows the top four candidates plus the selection when needed; the
interval strip includes every retained candidate. Coding probabilities include
the codec’s filtering, temperature adjustment, and integer allocation.

To regenerate the recordings, start the pinned local server and run:

```sh
.venv/bin/python scripts/export_sampler.py
```

Check the recordings against the archived covers and verify the browser’s exact
ciphertext reconstruction without running a model:

```sh
.venv/bin/python scripts/export_sampler.py --check
node website/test-sampler.cjs
```

The first paragraph is included in the cover text so the decoder can reconstruct
the model context. In opening-v1, we also bind it into key derivation. Use the CLI
to embed ciphertext from age, GPG, or another tool. Select `--compression raw` to
skip compression of data that has already been encrypted. The codec also applies
its own authenticated encryption.

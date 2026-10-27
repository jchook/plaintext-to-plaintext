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

# Shared prototype code

The experiment history and evidence live in [experiments/](../EXPERIMENTS.md).
This directory holds the shared implementations so experiments can compare the
same code without copying it into every run folder.

| File | Purpose |
| --- | --- |
| `p2p.py` | Original v1 codec and dedicated model server |
| `compact.py`, `source_codec.py` | Compact v2 framing, cover profiles, and lossless source coding |
| `opening.py`, `opening_demo.py` | Public opening paragraph variant and controlled pilot runner |
| `opening_validate.py` | Saved-cover rejection and externally restarted replay checks |
| `demo.py`, `compact_demo.py` | Separate-process round-trip runners |
| `test_p2p.py`, `test_compact.py` | Local tests with test predictors |
| `keys/alice.txt` | Public demonstration key, with source attribution |
| `web_demo.py`, `web/` | Guided local web demo using the opening-v1 codec |

## Setup

These instructions set up the local web demo from a fresh clone. Public hosting
can use the separate [static playground](../website/README.md), which replays
saved examples without inference. The live app binds to this computer only.

### Prerequisites

- Git and Python 3.10+ with the `venv` module. The current demo and tests have
  been exercised on Linux with Python 3.12. On Debian/Ubuntu, the `python3-venv`
  package supplies virtual-environment support.
- [Ollama](https://docs.ollama.com/quickstart), installed and running so it can
  download the model. Follow the [official Linux installation guide](https://docs.ollama.com/linux)
  on Linux. If the service is not running, start `ollama serve` in a separate
  terminal and leave it open while downloading.
- A compatible `llama-server` executable. Some Ollama installations bundle one;
  packaging varies. The codec starts a dedicated instance of that executable
  with a fixed CPU configuration. See [inference runtime](#inference-runtime)
  before proceeding if your installation does not include it.
- Disk space for the repository, Python environment, and roughly 1.9 GB of model
  weights. The inference runtime also needs RAM for weights, context, and work
  buffers. Inference runs on CPU; a GPU is optional for future configurations.

The prototype imports the Unix `fcntl` module. Native Windows is not currently
supported; use a Linux environment such as WSL2 and run these commands inside
that environment. macOS has not been validated for exact model replay here.

### One-command launcher

After installing the prerequisites above:

```sh
git clone https://github.com/jchook/plaintext-to-plaintext.git
cd plaintext-to-plaintext
./run-local.sh
```

The shell launcher creates `.venv` when needed and installs the declared Python
dependencies if they are missing. The Python launcher checks for a runtime before
downloading anything large, downloads the pinned model through Ollama when needed,
checks the actual model SHA-256 before starting a runtime it owns. It then verifies
model identity and exact replay, starts the web app, and opens the browser.
Keep the terminal open. Ctrl-C stops only server processes this launcher started;
an existing model server is left running.

Useful options:

```sh
./run-local.sh --check
./run-local.sh --no-browser --port 8001
./run-local.sh --url http://127.0.0.1:11535
```

`--check` still bootstraps Python dependencies, but does not download a model or
start servers. Without `--url`, it checks the local runtime and the model file's
checksum. With `--url`, it checks endpoint reachability; full compatibility and
replay checks run when launching. `--url` attaches an existing compatible endpoint
and never downloads or starts its model. The web app still uses the pinned model
and protocol; this option does not enable arbitrary chat models or the ordinary
Ollama API. Missing runtime paths and model-store locations can be configured
with the environment variables below.

The separate-terminal instructions below remain available for manual setup.

### 1. Clone and install Python dependencies

```sh
git clone https://github.com/jchook/plaintext-to-plaintext.git
cd plaintext-to-plaintext
python3 -m venv .venv
.venv/bin/python -m pip install -r poc/requirements.txt
```

`cryptography` is the only declared third-party Python dependency. The commands
use the virtual environment's Python directly, so shell activation is not needed.
Run subsequent commands from this repository root.

### 2. Download the model and start inference

```sh
ollama pull llama3.2:3b-instruct-q4_K_M
.venv/bin/python poc/p2p.py serve
```

Keep this terminal open. The dedicated model server listens on
`127.0.0.1:11535`; it is separate from the ordinary Ollama service used for the
download. Startup loads the downloaded model, then waits for codec requests.

### 3. Verify replay and start the web demo

Open a second terminal and change into the same `plaintext-to-plaintext`
directory. Run the replay check first:

```sh
.venv/bin/python poc/p2p.py probe
```

It should report `"exact_replay": true`. If it fails, follow the troubleshooting
table below before relying on encode/decode compatibility. Then start the demo:

```sh
.venv/bin/python poc/web_demo.py
```

Open **http://127.0.0.1:8000**. Keep both server terminals open while using the
demo. Press Ctrl-C in each to shut them down. The Python dependencies alone
are sufficient for the interface; there is no frontend build step.

### Inference runtime

The launcher searches for `llama-server` on `PATH` and in several paths relative
to the Ollama executable. You can select an existing compatible binary explicitly:

```sh
export P2P_LLAMA_SERVER="/absolute/path/to/llama-server"
.venv/bin/python poc/p2p.py serve
```

The model store defaults to `~/.ollama/models`. If Ollama downloaded the model
elsewhere, set `OLLAMA_MODELS` to that actual, readable directory before starting
the dedicated server:

```sh
export OLLAMA_MODELS="/absolute/path/to/ollama/models"
.venv/bin/python poc/p2p.py serve
```

That directory must contain the downloaded `blobs/sha256-…` file. Setting the
variable here does not move model files or reconfigure an already-running Ollama
download service. Both environment variables can be set together when needed.

The expected model SHA-256 is:

```text
dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff
```

The saved experiments record server build `b1-0f3a71be1`. The repository does not
yet distribute a pinned runtime installer or container. A different upstream
build may reject launcher flags or return different probabilities. Use a build
compatible with the launcher's arguments and API, then run `probe`; replaying
historical covers provides an additional compatibility check. Matching the model
name or passing `probe` alone does not establish compatibility with old covers
or another machine. Preserve the runtime, model, and protocol used to encode.

### Troubleshooting

| Symptom | Next step |
| --- | --- |
| Python cannot create `.venv` | Install your operating system's Python virtual-environment package, then repeat step 1. |
| `ollama pull` cannot connect | Start the Ollama application/service, or run `ollama serve` in another terminal, then retry the download. |
| `Set P2P_LLAMA_SERVER` | Locate your compatible `llama-server` executable and set its absolute path as shown above. Ollama installations that omit it need a compatible runtime supplied separately. |
| Missing pinned model | Download the exact tag above and check `OLLAMA_MODELS`. A system Ollama service may use a different user's model directory. |
| Server rejects a command-line flag | The installed inference build differs from the one used here. Use a compatible runtime; changing launch flags can change the inference behavior. |
| `Cannot reach …11535` or model unavailable in the page | Check that the dedicated `p2p.py serve` process is running and finished loading. Its terminal contains startup errors. |
| Replay check fails | Confirm the model/runtime and keep the dedicated server free of unrelated inference requests. The CLI's `--cold` option is available for experiments, but the web demo currently uses the default cache policy. |
| Web port 8000 is in use | Run `.venv/bin/python poc/web_demo.py --port 8001` and open `http://127.0.0.1:8001`. |
| Inference port 11535 is in use | Choose an unused port with `p2p.py serve --port 11536`; give `probe` and `web_demo.py` the matching `--url http://127.0.0.1:11536`. |
| Recovery fails after refreshing or on another tab | Restore the original key and temperature in Advanced controls, and paste the exact full cover. A new tab or refresh generates a different key. |
| Queue is full | Retry later. One request runs at a time; restarting the server discards its in-memory queue. |

## Web demo

After completing [setup](#setup), keep the dedicated model server running and
launch the browser interface from the repository root:

```sh
.venv/bin/python poc/web_demo.py
```

Open **http://127.0.0.1:8000**. Enter a short message and choose **Hide message**.
The demo generates cover text, decodes it with a fresh predictor, and compares
the recovered bytes before showing a verified result. **Try recovering it**
copies the cover and its original settings into the recovery form.

Advanced controls start collapsed. They let you rewrite the public opening
paragraph, select temperature 1.2 (default) or 1.0, change compression, and copy
or replace the random 256-bit key. The opening becomes part of the cover and is
read automatically during recovery. Keep the exact cover, key, temperature, and
pinned model/runtime to recover later; the key is not embedded in the cover.
Keys and messages are not persisted by the demo. Refreshing the page generates
a new key, so save the key separately before closing or refreshing the tab.

Standard compression chooses the smaller of raw bytes and DEFLATE without
source-model inference. Model compression is opt-in and sends the original
message to the local model. Encoding is limited to 512 UTF-8 bytes and recovery
to 32 KiB of cover text. One job runs at a time, including recovery verification;
up to 20 more wait in a first-in, first-out queue. The page shows your position,
how many requests are ahead, and an approximate start time. Estimates use the
median of the most recent 20 successful jobs per operation (encode or decode)
and account for elapsed time in the active job. No wait estimate is invented
before timing samples exist. Different message sizes and settings can make the
estimate change. You can leave the queue before your job starts. A full queue
returns HTTP 429 with a 60-second retry hint; rejected jobs are not resubmitted
automatically. The browser polls queued jobs every three seconds, running jobs
every second, and backs off when reconnecting without creating another job.

Generated cover text can reach the codec's 5,000-token limit. Local inference
may take several minutes. Progress checks stop work after 30 minutes; an
individual inference call can take longer to return. Waiting jobs expire after
30 minutes; cancellation and expiry release
their queued message and key. Completed jobs expire after 30 minutes and only the
latest 20 are retained in process memory. The browser polls with unguessable job
IDs; neither keys nor input messages are included in those URLs or access logs.

The demo binds only to loopback and checks Host/Origin on API requests. It is a
local development server, not a multi-user deployment. Hosting requires a
separately provisioned pinned model runtime, HTTPS, and deployment access
controls. The queue is bounded in process memory and is lost on restart; keep
the tab open while waiting. A public launch still needs edge rate limiting and
static-asset caching. Multiple app replicas would need a shared queue and job
store. The existing wire protocol and experiment artifacts are unchanged.
Use `--port 8001` for another web port or `--url http://127.0.0.1:11535` for
the dedicated inference endpoint. Use `--queue-size 10` to change the maximum
number of waiting requests. No additional Python dependencies are needed.

## Runtime and CLI

For setup and v1 format details, see the [v1 protocol](../experiments/001-baseline-v1/PROTOCOL.md).
For the current compact codec, see the [v2 protocol](../experiments/002-compact-v2/PROTOCOL.md)
and [measured results](../experiments/002-compact-v2/README.md).
The public-opening variant has separate
[protocol instructions](../experiments/003-opening-paragraph/PROTOCOL.md).

After [setup](#setup), with the dedicated model server running, use another
terminal in the repository root:

```sh
.venv/bin/python poc/p2p.py probe
.venv/bin/python poc/compact.py encode --key poc/keys/alice.txt --input experiments/001-baseline-v1/examples/key-message.txt --output /tmp/message.cover.txt --stats /tmp/message.encode.json
.venv/bin/python poc/compact.py decode --key poc/keys/alice.txt --input /tmp/message.cover.txt --output /tmp/message.recovered.txt --stats /tmp/message.decode.json
cmp experiments/001-baseline-v1/examples/key-message.txt /tmp/message.recovered.txt
```

Choose unused output paths. Both ends need the exact model/runtime, key bytes,
and matching protocol/profile. The default compact profile is `warm`; its size
results are promising. The [public-opening pilot](../experiments/003-opening-paragraph/README.md)
demonstrates topic steering while retaining prose-quality limitations.

```sh
.venv/bin/python -m unittest discover -s poc -p 'test_*.py' -v
.venv/bin/python experiments/verify.py
.venv/bin/python poc/demo.py
.venv/bin/python poc/compact_demo.py --repetitions 2
```

New demo runs go to a timestamped directory in the corresponding experiment's
`runs/` folder. Pass `--directory experiments/NNN-name/runs/<unique-run-id>` when
running a new experiment. Both runners locate their default paths relative to
the repository, so invocation from another working directory is also supported.

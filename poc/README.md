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

## Web demo

Start the dedicated model server using the runtime setup below, then run:

```sh
python3 poc/web_demo.py
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
to 32 KiB of cover text. One job runs at a time; generated cover text can reach
the codec's 5,000-token limit. Local inference may take several minutes. Progress
checks stop work after 30 minutes; an individual inference call can take longer
to return. Completed jobs expire after 30 minutes and only the latest 20 are
retained in process memory. The browser polls with unguessable job IDs; neither
keys nor input messages are included in those URLs or access logs.

The demo binds only to loopback and checks Host/Origin on API requests. It is a
local development server, not a multi-user deployment. Hosting requires a
separately provisioned pinned model runtime, HTTPS, and deployment access
controls. The existing wire protocol and experiment artifacts are unchanged.
Use `--port 8001` for another web port or `--url http://127.0.0.1:11535` for
the dedicated inference endpoint. No additional Python dependencies are needed.

## Runtime and CLI

For setup and v1 format details, see the [v1 protocol](../experiments/001-baseline-v1/PROTOCOL.md).
For the current compact codec, see the [v2 protocol](../experiments/002-compact-v2/PROTOCOL.md)
and [measured results](../experiments/002-compact-v2/README.md).
The public-opening variant has separate
[protocol instructions](../experiments/003-opening-paragraph/PROTOCOL.md).

From the repository root:

```sh
python3 -m pip install -r poc/requirements.txt
ollama pull llama3.2:3b-instruct-q4_K_M
python3 poc/p2p.py serve
```

In another terminal:

```sh
python3 poc/p2p.py probe
python3 poc/compact.py encode --key poc/keys/alice.txt --input experiments/001-baseline-v1/examples/key-message.txt --output /tmp/message.cover.txt --stats /tmp/message.encode.json
python3 poc/compact.py decode --key poc/keys/alice.txt --input /tmp/message.cover.txt --output /tmp/message.recovered.txt --stats /tmp/message.decode.json
cmp experiments/001-baseline-v1/examples/key-message.txt /tmp/message.recovered.txt
```

Choose unused output paths. Both ends need the exact model/runtime, key bytes,
and matching protocol/profile. The default compact profile is `warm`; its size
results are promising. The [public-opening pilot](../experiments/003-opening-paragraph/README.md)
demonstrates topic steering while retaining prose-quality limitations.

```sh
python3 -m unittest discover -s poc -p 'test_*.py' -v
python3 experiments/verify.py
python3 poc/demo.py
python3 poc/compact_demo.py --repetitions 2
```

New demo runs go to a timestamped directory in the corresponding experiment's
`runs/` folder. Pass `--directory experiments/NNN-name/runs/<unique-run-id>` when
running a new experiment. Both runners locate their default paths relative to
the repository, so invocation from another working directory is also supported.

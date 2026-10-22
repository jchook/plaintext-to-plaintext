# Shared prototype code

The experiment history and evidence live in [experiments/](../EXPERIMENTS.md).
This directory holds the shared implementations so experiments can compare the
same code without copying it into every run folder.

| File | Purpose |
| --- | --- |
| `p2p.py` | Original v1 codec and dedicated model server |
| `compact.py`, `source_codec.py` | Compact v2 framing, cover profiles, and lossless source coding |
| `opening.py`, `opening_demo.py` | Public opening paragraph variant and controlled pilot runner |
| `demo.py`, `compact_demo.py` | Separate-process round-trip runners |
| `test_p2p.py`, `test_compact.py` | Local tests with test predictors |
| `keys/alice.txt` | Public demonstration key, with source attribution |

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
results are promising, but the [next planned experiment](../experiments/003-opening-paragraph/README.md)
addresses its uneven prose quality.

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

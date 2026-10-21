# Plaintext to plaintext

An experimental codec that encrypts arbitrary bytes, then carries the encrypted
frame in model-generated prose. Decoding must recover the original bytes exactly.

Start with [Experiments and directions](EXPERIMENTS.md) for the short history,
results, decisions, and next experiment.

| Location | Contents |
| --- | --- |
| [experiments/](experiments/) | Numbered experiments, handoff READMEs, inputs, covers, recovered bytes, and measurements |
| [poc/](poc/README.md) | Shared codec implementations, tests, runners, and public demonstration key |
| [research/](research/README.md) | Archived papers and implementation references; [findings](research/summary.md) |
| [blog/concept.md](blog/concept.md) | Explanation of the original v1 construction |

From the repository root:

```sh
python3 -m pip install -r poc/requirements.txt
python3 -m unittest discover -s poc -p 'test_*.py' -v
python3 experiments/verify.py
```

The tests use local test predictors. The archive check compares saved bytes and
hashes; it does not rerun model inference. To generate and decode new covers,
follow the [runtime instructions](poc/README.md).

This prototype has demonstrated exact local recovery. Naturalness, statistical
detectability, phone performance, and compatibility across runtimes remain open.

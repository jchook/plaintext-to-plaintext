# HiTMS: A High-Throughput Multi-Stream Linguistic Steganography Framework

Research code for **linguistic steganography over LLM chat
dialogues**, with a single-stream baseline and a batched **multi-stream
(HiTMS)** protocol that hides several independent secret messages at once and
exploits GPU batching for much higher throughput.

A *Bob* model asks questions; an *Alice* model answers, secretly encoding the
payload into its token choices via a steganographic coder; Bob re-runs the model on
Alice's reply to recover the bits. Encoding and decoding are bit-exact, so the
secret is recovered losslessly.

## Highlights

- **Two coders**, both with bit-identical encode/decode:
  - **Arithmetic coding** (`arithmetic*.py`)
  - **Discop** (distribution-preserving, `discop*.py`)
- **Single-stream** protocol (`single_stream.py`): no framing overhead — every
  channel bit is payload (~100% utilization).
- **Multi-stream HiTMS** protocol (`protocol.py`): *m* secret streams fragmented
  across rounds, a PRF-driven stream→slot mapping, decoy slots, 16-bit length
  headers, and a filler keystream. Multiple responses per round are generated in
  **one batched forward pass**, so throughput scales with the batch size.
- **Reproducible experiment drivers** with deterministic prompt streams,
  per-trial checkpoint/resume, and crash/void-reroll handling.
- **LLM-as-a-judge** imperceptibility evaluation (naturalness + coherence).

Models used in the experiments: `meta-llama/Llama-3.2-3B-Instruct` and
`google/gemma-3-4b-it`. Datasets: creative/open-ended subsets of
`databricks/databricks-dolly-15k` and `HuggingFaceH4/no_robots`.

## Repository layout

| Path | Description |
|------|-------------|
| `arithmetic.py`, `arithmetic_batch.py` | Arithmetic-coding stego (single + batched stream encoder/decoder). |
| `discop.py`, `discop_batch.py` | Discop stego coder + shared PRG (single + batched). |
| `utils.py` | Shared helpers (bit/int conversion, entropy, top-k, sentence-finish checks). |
| `protocol.py` | Multi-stream HiTMS protocol (stream mapping, decoys, headers, filler). |
| `single_stream.py` | Single-stream protocol (no framing; truncate at the L-th bit). |
| `round_trip.py`, `batch_round_trip.py` | Minimal one-shot round-trip demos/tests. |
| `multi_round_demo.py` | Multi-stream trial runner (`run_trial`) + verbose single-trial demo. |
| `single_stream_demo.py` | Single-stream trial runner (`run_single_trial`) + demo. |
| `run_sweep.py` | Multi-stream sweep over {model}×{pool}×{coder}, resumable. |
| `run_single_sweep.py` | Single-stream counterpart sweep. |
| `run_scaling_sweep.py` | Stream-count scaling sweep (x ∈ {1,2,4,8,16,32,64}), any model/pool/coder. |
| `run_x1_shards.py`, `run_x1_finish.sh`, `merge_x1_shards.py` | x=1 ablation: shard one cell across GPUs, then merge with coverage checks. |
| `judge_quality.py` | LLM-as-a-judge imperceptibility scorer (one QA per call, resumable). |
| `gen_cover.py` | Payload-free "cover" text generation (steganalysis reference). |
| `steganalysis_bert.py` | Cover-vs-stego detector (BERT / RoBERTa / DeBERTa-v3 / ELECTRA). |
| `export_data.py` | Builds the publishable summary-only mirror in `data/`. |
| `build_question_pool.py`, `build_norobots_pool.py` | Build the question pools from HF datasets. |
| `*_creative_questions.json` | Pre-built question pools. |
| `legacy/` | Earlier scripts / pools, kept for reference. |

## Data

[`data/`](data/) holds the results of every experiment in the paper — capacity,
throughput, utilization, judge scores and detector AUROCs — as one JSON object
per trial. See [`data/README.md`](data/README.md) for the full schema.

The generated stegotext itself is **not** included: the raw logs embed the
question and response for every fragment, which makes them ~1 GB, so
`export_data.py` strips those fields and keeps every measurement (~24 MB). All
drivers are seeded, so re-running a sweep regenerates the text exactly.

> The raw output directories (`sweep_logs/`, `single_sweep_logs/`,
> `scaling_logs/`, `judge_logs/`, `cover_logs/`, `run_logs/`,
> `steganalysis_logs/`) are **gitignored** — they are large (the last one holds
> multi-GB trained detector checkpoints) and fully regenerable.

## Installation

```bash
conda create -n ems python=3.10 -y && conda activate ems
pip install torch transformers datasets numpy
pip install openai          # only needed for judge_quality.py
```

A CUDA GPU is required to run the LLMs. The Llama and Gemma checkpoints are
gated on the Hugging Face Hub, so run `huggingface-cli login` (with access
granted to those models) before first use.

## Usage

Build the question pools (once):

```bash
python build_question_pool.py        # -> dolly15k_creative_questions.json
python build_norobots_pool.py        # -> norobots_creative_questions.json
```

Single verbose trial (sanity check):

```bash
# multi-stream
CUDA_VISIBLE_DEVICES=0 python multi_round_demo.py
# single-stream
CUDA_VISIBLE_DEVICES=0 python single_stream_demo.py
# override model / coder / pool via env
ROUND_TRIP_MODEL=google/gemma-3-4b-it STEGO_ALGORITHM=discop \
  STEGO_QUESTION_POOL=norobots_creative_questions.json \
  CUDA_VISIBLE_DEVICES=0 python multi_round_demo.py
```

Full experiments (resumable — re-run the same command to continue):

```bash
# multi-stream (8 streams x 1024 bits), all model/pool/coder combos, 500 trials
CUDA_VISIBLE_DEVICES=0 python run_sweep.py --trials 500
# single-stream baseline
CUDA_VISIBLE_DEVICES=0 python run_single_sweep.py --trials 500
# stream-count scaling (dolly + Llama + Discop)
CUDA_VISIBLE_DEVICES=0 python run_scaling_sweep.py --x-values 4 8 16 32 64
```

Imperceptibility evaluation (needs an OpenAI key in `OPENAI_API_KEY` or a
local `OPENAI_API_key.txt`, both gitignored):

```bash
python judge_quality.py --dry-run        # plan only, no API calls
python judge_quality.py --limit 2        # tiny live smoke test
python judge_quality.py                  # full run (resumable)
python judge_quality.py --aggregate-only # recompute the score table
```

## Reproducibility

Each driver fixes its seeds (prompt shuffling, payload sampling, sampling RNG,
`torch.manual_seed`) and consumes prompts from a deterministic, pass-aware
prompt stream, so a full sweep is reproducible end-to-end and resumes exactly
from its checkpoint after an interruption.

## Notes

- This is research code accompanying a paper in progress; APIs may change.
- Never commit secrets — `OPENAI_API_key.txt`, `*.key`, and `.env` are ignored.

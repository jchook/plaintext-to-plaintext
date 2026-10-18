# Addressing Tokenization Inconsistency in Steganography and Watermarking

Reference implementation for **Ruiyi Yan and Yugo Murawaki, "Addressing
Tokenization Inconsistency in Steganography and Watermarking Based on Large
Language Models", EMNLP 2025** ([paper](https://aclanthology.org/2025.emnlp-main.361/)).

When Alice sends Bob a stegotext or a watermarked text, the token list travels
as a *string*: it is detokenized on the way out and retokenized on the way in.
Subword tokenizers do not always reproduce the original split — `["_no",
"body"]` comes back as `["_nobody"]` — and that **tokenization inconsistency
(TI)** silently breaks steganographic extraction and weakens watermark
detection.

The paper shows that the tokens responsible for TI are **infrequent** (well
under 1% of generated tokens) and often **temporary** (the inconsistency heals
by itself a token or two later), and turns those two properties into two
methods:

* **Stepwise verification** for steganography — filter candidate-level
  inconsistent tokens out of the candidate pool at every step, so sender and
  receiver always see the same pool. Extraction is exact by construction, at
  `O(k)` cost per step instead of the `O(k²)` of prior disambiguation methods.
* **Post-hoc rollback** for watermarking — tolerate an inconsistency for an
  observation period of `q` tokens, and only if it has not healed by then, roll
  back and resample without the offending token.

---

## Installation

```bash
git clone https://github.com/ryehr/Consistency.git
cd Consistency
pip install -e ".[experiments,dev]"      # or: pip install -r requirements-dev.txt
```

Python ≥ 3.10. Developed against torch 2.5 / transformers 4.46; tested up to
torch 2.13 / transformers 5.14.

The three models of the paper are gated or large; `huggingface-cli login` first
if needed. Everything also runs on a small model — the tests use
`Qwen/Qwen3-0.6B` — which is the quickest way to check your setup.

---

## Quick start

```python
from tokenization_consistency import load_model_and_tokenizer, resolve_spec, roundtrip

spec = resolve_spec("llama2-7b")
model, tokenizer = load_model_and_tokenizer(spec)

result = roundtrip(
    model, tokenizer,
    prompt="Finding a high quality photographer for your family portrait,",
    message_bits="1011" * 32,          # 128 bits
    strategy="consistency", top_k=128,
)
print(result.correct)                   # True: Bob recovered the message exactly
print(result.embed.bits_per_token, result.embed.kld)
print(result.embed.text)
```

```python
from tokenization_consistency import build_scheme, detect, generate
from tokenization_consistency.models import usable_vocab_size

scheme = build_scheme("lefthash", usable_vocab_size(model, tokenizer),
                      key=2024, device=model.device, gamma=0.5, delta=2.0)
watermarked = generate(model, tokenizer, "In fact, there are currently over a million",
                       scheme, num_tokens=200, rollback_period=2)   # q = 2
print(detect(scheme, tokenizer, text=watermarked.text))
```

---

## Reproducing the paper

```bash
# Section 2 / Tables 1-4 and 19: how often TI appears, and whether it heals.
# Also prints the observation period q that Appendix F derives.
python scripts/run_investigation.py --model llama2-7b \
    --token-nums 25 50 100 200 400 --samples 1000

# Section 4.1 / Tables 5-7: steganography, our method against the baselines.
python scripts/run_steganography.py --model llama2-7b \
    --strategy consistency basic mwis syncpool none \
    --top-k 4 8 16 32 64 128 256 512 1024 2048 4096 --samples 500
python scripts/aggregate.py steganography --input-dir results/steganography

# Section 4.2 / Table 8: watermarking, TI-unaware against post-hoc rollback.
python scripts/run_watermark.py --model llama2-7b \
    --scheme lefthash unigram gumbel --tokens 200 --samples 500

# Section 4.2.1 / Tables 11-13: robustness under a replacement attack.
python scripts/run_attack.py \
    --input results/watermark/llama2-7b_lefthash_q2_len200.tsv \
    --attack-probability 0.2 0.4
python scripts/aggregate.py watermark --input-dir results/watermark \
    --attack-dir results/attack
```

`--model` accepts a preset (`llama2-7b`, `swallow-7b`, `qwen2.5-7b`,
`qwen3-0.6b`), a raw Hugging Face id, or the original scripts' numeric index
(`0`, `1`, `2`). Each preset carries the paper's language, prompt convention and
observation period. Prompts stream from multilingual C4 and are cached under
`results/prompt_cache/`; set `TOKCON_PROMPT_FILE` to a JSONL file with a `text`
field to run fully offline.

`docs/paper_mapping.md` maps every section, table and algorithm to the code that
implements it.

---

## Repository layout

```
src/tokenization_consistency/
├── tokenization.py     TI definitions (SITs, CITs) and Algorithm 1
├── pools.py            candidate pools: none / basic / mwis / syncpool / consistency
├── coding.py           arithmetic coding, shared by embedding and extraction
├── steganography.py    Algorithms 2 and 3, plus a round-trip check
├── watermark.py        LeftHash / SelfHash / Unigram / Gumbel, and Algorithm 4
├── investigation.py    the Section 2 measurements
├── attacks.py          random-replacement attack on watermarked text
├── metrics.py          perplexity, AUROC, BPT interval grouping
├── models.py           model registry, prompts, cached step-by-step decoding
└── io_utils.py         result TSVs and run metadata
scripts/                command-line entry points (see above)
tests/                  unit tests, plus end-to-end tests on a small model
legacy/                 the original four scripts, unchanged
docs/paper_mapping.md   paper -> code map
```

Results are written to `results/` as TSV, one row per sample, with a JSON
sidecar recording the arguments, git revision and environment of the run.

---

## Tests

```bash
pytest -m "not slow"    # ~20 s, no model weights needed beyond a tokenizer
pytest                  # adds end-to-end tests on Qwen3-0.6B (needs a GPU)
```

The end-to-end tests are the ones that check the paper's central claim
directly: a 48-bit message is embedded and then extracted by a receiver that
sees only the stegotext, and must come back bit for bit. `tests/test_pools.py`
additionally checks the refactored MWIS baseline against the original
implementation on random graphs, so the baseline comparison stays honest.

---

## What changed relative to the original release

This is a refactor of the proof-of-concept code that accompanied the paper. The
original scripts are preserved unchanged in `legacy/`.

**New capability**

* **Steganographic extraction (Algorithm 3) is implemented.** The original code
  approximated extraction success by checking whether the generated token list
  survived retokenization. There is now a real receiver, so extraction accuracy
  is *measured*: `roundtrip()` embeds and extracts, and the scripts report the
  exact-match rate. This also makes the error rates of Appendix D.3
  reproducible via `--strategy none`.
* **Section 2 is reproducible.** `scripts/run_investigation.py` computes the
  text-, token- and candidate-level inconsistency rates, the temporariness rate,
  and the recovery-distance distribution behind the choice of `q`.
* **Evaluation and aggregation.** Perplexity, AUROC and watermark strength are
  computed in-process, and `scripts/aggregate.py` turns raw TSVs into the
  paper's tables, including the "fewer than 20 samples" rule.
* **A real `selfhash` scheme.** See the note in `docs/paper_mapping.md`.

**Corrections** (each changes numbers, so they are listed explicitly)

* The arithmetic coder now anchors its interval boundaries to the ends of the
  current interval. Cumulative float sums fall short of 1.0, and the resulting
  gap made the original encoder abort runs with `float error, again!`.
* Watermark KL divergence was computed as
  `F.kl_div(probabilities, original_probabilities, log_target=True)`, which
  expects log-probabilities on both sides and was fed plain probabilities. It is
  now `KL(watermarked ‖ original)` in nats.
* The green-list z-score divided by `sqrt((i+1)·γ(1-γ))` while summing over `i`
  scored tokens, an off-by-one against the formula in Appendix D.5.
* The replacement attack sliced the batch dimension (`tokens[:i+1]`) instead of
  the sequence dimension, so every replacement was conditioned on the whole
  partially attacked sequence rather than on its left context.
* An empty candidate pool left `selected_index` unbound and raised `NameError`;
  a zero-length generation divided by zero. Both are now typed failures recorded
  in the output.

**Cleanups**

* `requirements.txt` was a `pip freeze` full of `file:///croot/...` paths and
  could not be installed anywhere; it is now a small set of lower bounds.
* Dead imports that break on current torch (`torch.onnx.symbolic_opset9`,
  `sympy.logic.inference`, `objgraph`) are gone.
* `model.resize_token_embeddings(len(tokenizer.vocab))` mutated pretrained
  weights to work around output layers wider than the tokenizer vocabulary.
  The unreachable logits are masked instead; the set of reachable tokens is the
  same.
* Sender and receiver share one KV-cached decoding loop (`LMStepper`), which is
  both much faster than a full forward pass per token and bit-identical between
  the two sides — a requirement for exact extraction.
* Candidate verification batches its `decode`/`encode` calls, so Algorithm 1
  runs through the tokenizer's Rust batch path rather than a Python loop.
* Pools are ordered by descending probability everywhere. The original derived
  one pool from a Python `set`, whose iteration order is arbitrary.

**Not included**

* The steganalysis discriminator of Appendix D.2 (fine-tuned BERT) and the
  ACC column of Tables 5–7.
* The GPT-4o paraphrasing attack of Appendix H.
* The experiment result files themselves. The original repository shipped empty
  placeholder files under `Address_glitch_*_data/`; those directories have been
  replaced by `results/`, which the scripts populate.

---

## License

MIT — see [LICENSE](LICENSE). The `legacy/` scripts are covered by the same
terms. Model weights and the C4 dataset carry their own licenses.

## Citation

```bibtex
@inproceedings{yan-murawaki-2025-addressing,
    title = "Addressing Tokenization Inconsistency in Steganography and Watermarking Based on Large Language Models",
    author = "Yan, Ruiyi  and
      Murawaki, Yugo",
    editor = "Christodoulopoulos, Christos  and
      Chakraborty, Tanmoy  and
      Rose, Carolyn  and
      Peng, Violet",
    booktitle = "Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing",
    month = nov,
    year = "2025",
    address = "Suzhou, China",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2025.emnlp-main.361/",
    doi = "10.18653/v1/2025.emnlp-main.361",
    pages = "7076--7098",
    ISBN = "979-8-89176-332-6"
}
```

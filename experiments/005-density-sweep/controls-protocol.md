# Secondary ordinary-generation diagnostic

Declared 2026-10-22, after inspection of early blinded sweep reviews and before
any control generation. This is a post-hoc diagnostic, separate from the frozen
40 payload-carrying trials. No sweep settings, rubric, or acceptance criteria change.

Question: does the same model and public-opening wrapper produce repetition,
unsupported claims, role drift, prompt leakage, or grammatical failures during
ordinary generation too?

A pre-control hypothesis is that suppressing EOS while requiring enough bits to
represent the frame can force generation beyond a natural ending, into repeated
closings, alternate drafts, or writing advice. Ordinary generation with EOS can
help assess this explanation. It remains confounded with candidate filtering
and different stopping lengths.

Five samples, one at each temperature 0.8/1.0/1.2/1.4/1.6. Same rendered prompt,
conference opening, pinned model and single-slot server. Explicit top_k64,
top_p1, min_p0, typical_p1, repeat_penalty1, presence_penalty0,
frequency_penalty0, dry_multiplier0, xtc_probability0. Fixed distinct random seeds
202610220 through 202610224 assigned before generation. Interleave conditions
using seed 202610225. Use normal server tokenization and EOS termination, with a
512 generated-token limit. Count reaching that limit explicitly; do not silently
treat a length-truncated cover as naturally finished. Full request and response,
model/runtime configuration, timing, exact opening and cover are retained.

Unlike the stego sampler, ordinary generation does not enforce the codec's
prefix-free visible-token restrictions, map payload bits, or append its greedy
sentence-completion suffix. Thus these controls can reveal shared failure
modes but cannot attribute differences to temperature alone or isolate each
codec feature. One sample per temperature is insufficient for frequency estimates.
They contain no payload and are never included in density/recovery aggregates.

Use the original seven-dimension blinded machine-review rubric and >=11 threshold
with no zero on fluency/coherence/roles. Save a separate randomized opaque-ID
review batch and keep its temperature mapping separate until grading is saved.
The supplied opening is context, excluded from continuation scores.

Run only after the forty sweep trials finish, with no competing server requests:

```sh
python3 experiments/005-density-sweep/ordinary_controls.py
```

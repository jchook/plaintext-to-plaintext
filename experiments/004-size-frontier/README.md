# 004: Size, plausibility, and distribution control

Status: planned, 2026-10-22. Predecessor:
[opening-paragraph pilot](../003-opening-paragraph/README.md).

## Question

How small can the complete cover become while retaining authenticated exact
recovery and acceptable correspondence? Measure writing plausibility and
detectability separately. The [research follow-up](../../research/2026-10-22-size-plausibility/README.md)
contains the literature, rationale, and retrospective size breakdown.

Hypotheses:

- Short public openings lower total cover size enough to justify any change
  in continuation quality.
- Adaptive control of token probabilities offers a better size/quality tradeoff
  than fixed temperature. This is a hypothesis, not a result from our codec.
- Replacing the arithmetic coder while holding its distribution fixed yields
  a smaller size benefit than changing the available distribution.

Keep exact bytes and authentication mandatory. Set operational size limits per
message category before generation. Count an encode that exceeds its limit as
a failure; truncating a cover is not a smaller successful transmission.

## Setup and attempts

No new inference attempts have run. The existing codec remains unchanged.
Use staged comparisons so that changes remain attributable:

1. Add per-step diagnostics for candidate support, entropy, expected visible
   bytes, exclusion reasons, distribution distortion, and arithmetic progress.
   Record what reference distribution each diagnostic uses. Verify the existing
   003 control still produces authentic exact recovery before new conditions.
2. Compare the current conference/STEM/history openings with short counterparts
   of roughly 60–100 bytes. Hold model, wrapper version, coder, framing, and
   temperature fixed. The supplied opening still appears verbatim in the cover.
3. Fix the chosen opening policy and compare fixed temperature with an OD-Stega
   inspired adaptive KL budget. Add a uniform rank-based baseline over a
   decodable candidate set. Freeze the candidate policy within this comparison;
   use a separate comparison for widening or changing the candidate set.
4. If diagnostics show material coder loss, compare RRC or ANStega on matched
   distributions. Account for all auxiliary state and preserve the real
   visible-text channel. Token-ID-only recovery is insufficient.

Use independent repetitions, not repeated encodes of one easy sentence alone.
Include tiny inputs, varied paragraphs, incompressible bytes, and Unicode.
Choose the corpus, repetitions, exact parameters, evaluation rubric, and
size limits before implementing the runner. The pilot's two repetitions per
fixture are insufficient to estimate a stable frontier.

Version any changed template or protocol. Before inference, commit the measured
implementation and record exact commands, source/model hashes, runtime build,
prompts, settings, source packing, and interleaving seed. Save every attempted
condition, including failures and timeouts, under `runs/<unique-id>/`.

## Results and evidence

The only current evidence is the [retrospective audit](../../research/2026-10-22-size-plausibility/audit.json)
of experiment 003's 32 saved trials. It supplies the starting size budget.
It is not a new sampler experiment.

Report full bytes, component bytes, words, tokens, payload bits per transmitted
byte, encoding/decoding time, and authenticated recovery. Separate the supplied
opening from the continuation in both accounting and qualitative assessment.

Use blind plausibility assessment with a fixed rubric: purpose, fluency,
sender/recipient continuity, unsupported assertions, repetition, natural ending,
and length appropriate to the scenario. Identify machine assessments as such.
Choose an acceptance threshold before unblinding conditions.

Detection evaluation needs two control sets: ordinary output from the same
generator and legitimate correspondence in the intended genre. Report held-out
AUROC and detection rate at declared false-positive rates, with uncertainty.
Split by source/thread/opening family to reduce leakage. Do not let a repeated
opening or train/test near-duplicates make the comparison trivial. Also test
whole covers without matching away length; a length-only baseline helps show
whether size itself explains separation. A secondary length-matched evaluation
can isolate stylistic differences. A small pilot should not claim universal
undetectability, and proxy KL is not a measured detection rate.

## Decision and remaining gaps

Retain the public-opening interface and authenticated byte equality. Optimize
complete bytes before treating a different arithmetic coder as the answer.
The candidate-set and sampler changes may alter quality and detection in
different directions. Keep those results visible separately.

For a future UI, the provisional slider labels are “closer to ordinary
generation” and “shorter cover.” Pick settings from measured non-dominated
configurations rather than assuming temperature maps monotonically to quality.
Display the expected size range and measured quality/detection evidence for
each setting. Calibration remains future work.

## Next step

Implement diagnostics and run the short-opening comparison first. Freeze the
corpus and rubric before the adaptive-sampler comparison. At closeout, record
the implementation and evidence commit IDs, actual results, and the selected
direction in [Experiments and directions](../../EXPERIMENTS.md).

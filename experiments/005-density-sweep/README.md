# 005: Five-setting density sweep

Status: planned, 2026-10-22. Predecessor: [004 plan](../004-size-frontier/README.md).
The user requested a density/plausibility experiment now. This bounded pilot
supersedes 004's short-opening-first staging for this comparison only.

## Question

How does fixed temperature affect full transmitted size, authenticated recovery,
and correspondence plausibility? This tests a simple available control, not an
adaptive sampler or error correction. Higher temperature is not assumed to
improve useful density monotonically.

## Frozen setup, before inference

Five temperatures: **0.8, 1.0, 1.2, 1.4, 1.6**. All else is held fixed:
opening-v1 wrapper, conference-followup public opening, top-64 candidate request,
prefix-free candidate restrictions, arithmetic coder, automatic lossless source
packing, public demonstration key, pinned Llama 3.2 3B Q4_K_M model and dedicated
single-slot CPU runtime. `codec.py` widens the temperature whitelist in memory;
no historical implementation or format is edited. Temperatures 1.0 and 1.2
retain exactly the existing protocol configuration. The receiver must share the
selected temperature; no per-message control signaling is included in this pilot.

Inputs: `key-message` (16 bytes), `paragraph` (238 bytes), `unicode` (original
fixture including whitespace), and `binary` (64 deterministic random bytes).
Two independent randomized-encryption repetitions per cell: **40 trials**.
Interleave temperatures within each payload and repetition using seed 20261022.
The wider range replaces an initial unrun 0.9–1.3 proposal before protocol freeze.

Limits: 5,000 generated continuation tokens, 8,000 complete cover bytes,
3,600 seconds per encode/decode phase. Any limit violation is a failed attempt;
preserve covers and logs, never truncate a cover and count it as success.
Each success requires ChaCha20-Poly1305 authentication and byte equality in a
separate decoder process. A startup 003 control replay checks compatibility.

Before inference commit the runner/protocol; run metadata records source commit,
code snapshots/hashes, exact commands, configuration, model identity, server
properties/build and timestamps. Preserve every attempt including failures.
Actual model SHA256 is checked before server startup and saved separately.
No API charges: inference is local; report wall time and model calls instead.

## Frozen plausibility assessment

Use randomized opaque cover IDs, with the condition mapping stored separately.
Review the full cover for contextual continuity, but score supplied opening
and generated continuation separately: a good copied opening does not improve
the continuation's score. Reviewers must not view the mapping until scores are
saved. These are machine assessments, not human ratings or a detection test.

For each dimension assign 0 (clear failure), 1 (noticeable weakness), or 2
(acceptable ordinary correspondence):

- Fluency: grammatical and idiomatic language.
- Coherence/purpose: continuation follows the conference email's purpose.
- Sender/recipient consistency: stable roles and natural address.
- Unsupported claims: no conspicuous invented prior exchanges or obligations.
- Repetition: no unnecessary repeated statements or requests.
- Ending: a complete, natural stopping point.
- Length: proportionate to the email purpose, without obvious padding.

Exploratory acceptance threshold: sum at least 11/14, with no zero in fluency,
coherence/purpose, or sender/recipient consistency. Report dimension scores and
failure reasons, not just a composite. Reviewer blinding cannot hide text length
or visible linguistic clues. Forty samples cannot establish a production quality
frontier, reliable failure probability, or low statistical detectability.

## Commands

```sh
python3 -m unittest discover -s poc -p 'test_*.py' -v
python3 experiments/005-density-sweep/run.py --dry-run --directory /tmp/density-sweep-schedule-20261022
python3 poc/p2p.py serve
python3 experiments/005-density-sweep/run.py --directory experiments/005-density-sweep/runs/pilot-20261022
```

Report full/component bytes, words, generated tokens, payload bits/full cover
byte, frame bits/token, entropy diagnostics, phase time, and exact recovery.
Summarize each input separately and across the balanced corpus. Do not rank
methods by pooled payload bits/token without accounting for packing and framing.

## Results and decision

Pending. Historical evidence is not a new inference result. Implementation,
evidence, and closeout commit IDs will be recorded after execution.

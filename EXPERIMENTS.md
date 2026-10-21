# Experiments and directions

Updated 2026-10-21. Read down the table for the path so far; each handoff contains
the evidence and the reasons for the next step. Experiment numbers describe the
order of ideas, not separately committed development stages.

| Step | Status | What we tried and learned | Handoff |
| --- | --- | --- | --- |
| 000: Embedding sketches | Archived, incomplete | Tried geometric word substitution. No demonstrated reversible sentence codec or measured round trip survives in the archive. | [Sketches](experiments/000-embedding-sketches/README.md) |
| 001: Reproducible v1 codec | Completed local trial | Encrypted bytes carried by arithmetic-coded Llama output recovered exactly in four saved cases, including Unicode and empty input. The 53-byte warning needed 2,635 cover bytes; expansion became the next problem. | [Baseline](experiments/001-baseline-v1/README.md) |
| Literature review | Archived reference work | Identified precedents, tokenization and runtime risks, and the need to measure retained entropy and compress before encryption. Paper results were not reproduced here. | [Research findings](research/summary.md) |
| 002: Compact v2 | Completed local trial | Removed padding, added lossless source compression, and compared prompts and temperature. All 21 completed round trips recovered exactly; a 238-byte paragraph used 1,104–1,164 cover bytes. Prose sometimes became conspicuously odd. | [Compact results](experiments/002-compact-v2/README.md) |
| 003: Opening-paragraph steering | Planned, unrun | Test whether a supplied paragraph gives the cover a consistent voice. Compare a style example in the prompt, then a visible public opening, while measuring readability separately from cover size. | [Experiment plan](experiments/003-opening-paragraph/README.md) |

## Where we are

Exact recovery works in the recorded local model/runtime. Compact v2 is our
current size baseline. Its arithmetic rate is close to the measured filtered
entropy, so replacing the coder alone has no demonstrated large benefit.
The small trial does not establish a stable ranking of prompt variants.

The immediate problem is prose quality. The current prompt asks for observations
from an unfamiliar town, invented names, and small mishaps; `warm` raises the
temperature to 1.2. The saved paragraph starts at a motel smelling of stale smoke.
Those prompt and temperature choices are plausible causes of the tone, but their
effects on readability have not been isolated. The next experiment should do that.

## Direction and decisions

1. Keep exact bytes and authenticated failure as requirements. A better-sounding
   paraphrase of the secret is not successful recovery.
2. Test the [opening-paragraph idea](experiments/003-opening-paragraph/README.md)
   before pursuing more capacity. Compare 1.0 and 1.2 under the same runtime and
   source-compression policy; accept some extra cover length if readability improves.
3. Evaluate full transmitted size, including any visible opening paragraph.
   Report readable continuation quality separately so copying a good paragraph
   cannot improve the quality score by itself.
4. Later, compare less restrictive token selection and alternative coders under
   matched conditions. Keep cross-runtime replay, edit tolerance, and throughput
   as separate questions with separate experiments.

## How to record the next experiment

Create `experiments/NNN-short-name/README.md` before running it. Use the
[handoff template](experiments/TEMPLATE.md), then add a one-sentence entry above.
Save runs under that experiment's `runs/<unique-run-id>/` directory. The runners
create fresh directories and refuse to overwrite them.

Keep each input, exact cover, recovered bytes, process statistics, logs, and
`results.json`. Keep failed and interrupted attempts, explain why they stopped,
and distinguish them from completed trials. Retain individual repetitions even
when adding aggregate summaries. Text and diagnostic logs belong in Git;
model weights and Python caches do not.

Record the source commit before a run, the exact command, prompt/configuration,
model hash, runtime build, and any changes made between attempts. At closeout,
write what the evidence supports, what remains uncertain, the decision, and the
next question. Commit the implementation and run evidence, then the closeout;
use the actual commit IDs in the handoff. Do not reconstruct a finer chronology
than the surviving records support.

## Checkpoints and archive integrity

- `ec98261` contains the early sketches and original POC together.
- `555afcd` adds the explanation and literature archive.
- `6e80812` preserves the previously uncommitted compact experiment, including
  the failed Unicode scoring log, before this reorganization. It is the source
  revision for the compact verification record's five code hashes.

The reorganization keeps raw evidence byte-for-byte, including historical paths
inside JSON and logs. [migration.json](experiments/migration.json) maps those old
paths to their current locations and records hashes for all 198 moved non-Markdown
files. Run `python3 experiments/verify.py` to check the archive and local handoff
links. Historical validation records describe past inference runs; the archive
check does not claim a fresh model replay.

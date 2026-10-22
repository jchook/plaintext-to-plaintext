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
| 003: Opening-paragraph steering | Completed pilot | All 32 round trips recovered exactly; supplied openings steered the reviewed samples into conference/STEM/history emails. Covers grew, and recipient-role slips and invented prior conversations remain. Seven rejection checks and two restart decodes passed. | [Results and handoff](experiments/003-opening-paragraph/README.md) |

## Where we are

Exact recovery works in the recorded local model/runtime. Compact v2 is our
current size baseline. Its arithmetic rate is close to the measured filtered
entropy, so replacing the coder alone has no demonstrated large benefit.
The small trial does not establish a stable ranking of prompt variants.

The immediate problem is prose quality. The old prompt asks for observations
from an unfamiliar town, invented names, and small mishaps. Experiment 003's
versioned wrapper and public opening changed the reviewed continuations into
the requested email topics. The 238-byte payload's mean full covers at 1.2 were
1,710.5–1,887.5 bytes, versus 1,467 for the warm control, with two trials per cell.
Opening v1 remains a prototype: the agent review found role changes, repeated
questions, and invented conversational history. Its wrapper and opening were
tested together, so their separate effects remain unknown.

## Direction and decisions

1. Keep exact bytes and authenticated failure as requirements. A better-sounding
   paraphrase of the secret is not successful recovery.
2. Keep the [public-opening interface](experiments/003-opening-paragraph/README.md)
   for further experiments. Next compare a new wrapper version that maintains
   sender/recipient roles and avoids inventing earlier exchanges. Preserve v1
   and compare against it; stronger instructions are not yet a demonstrated fix.
3. Evaluate full transmitted size, including the public opening paragraph.
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
- `7ce7883` pins the opening v1 implementation, tests, and pilot runner before
  collecting all 32 trials. Its measured sources are unchanged in the run snapshot.

The reorganization keeps raw evidence byte-for-byte, including historical paths
inside JSON and logs. [migration.json](experiments/migration.json) maps those old
paths to their current locations and records hashes for all 198 moved non-Markdown
files. Run `python3 experiments/verify.py` to check the archive and local handoff
links. Historical validation records describe past inference runs; the archive
check does not claim a fresh model replay.

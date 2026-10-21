# 003: Opening-paragraph steering

Status: planned, unrun. Proposed on 2026-10-21 after the
[compact v2 trial](../002-compact-v2/README.md). This folder contains the design
and a starting paragraph, with no measured improvement claimed yet.

## Question

Can a supplied first paragraph steer the cover toward ordinary, consistent prose
without losing exact recovery? The user's concern is that the current output
reads like an exaggerated travel narrative. The aim is readable continuation in
a chosen voice, even if a lower temperature requires more cover bytes.

The existing `varied` prompt asks for an unfamiliar town, invented details,
overheard conversations, and small mishaps. `warm` uses the same prompt at 1.2.
The [saved paragraph cover](../002-compact-v2/runs/main/paragraph.warm-auto.1.cover.txt)
opens at a motel with stale smoke and later introduces ominous signs and a gaunt
café owner. That is evidence of the unwanted tone, not evidence that an opening
paragraph fixes it. Temperature, prompt content, the small model, and candidate
filtering may each affect the result.

## Two versions of the idea

| Condition | Context supplied to the model | What the receiver needs |
| --- | --- | --- |
| Style paragraph in the generic prompt | Quote the paragraph as an example of voice, then request prose in that voice | Exact shared prompt/profile, including the example |
| Visible opening paragraph | Prefill the assistant response with the exact paragraph, then embed the encrypted frame in the continuation | Opening from the cover and an agreed boundary and tokenization rule |

Start with the prompt example because the current profile mechanism already
binds a fixed prompt into key derivation and authentication. If it works, test
the visible-opening version, which permits a public per-message opening and
provides a natural transition into the generated text.

The paragraph describes the cover's subject and voice. It must not be copied
from the private payload: putting private message text in the prompt or visible
opening would disclose that text. The original payload is still encoded in full
and must be recovered byte-for-byte. This experiment does not test disclosure
of a deliberately public part of the payload.

## Starting fixture and proposed prompt

Use [opening.txt](opening.txt) as the initial fixed example. It is a short update
about returning books to a library. Keep those UTF-8 bytes in the run record.
The proposed generic instruction is:

```text
Write an ordinary personal update in the voice of the example paragraph below.
Keep the same point of view and tense. Use straightforward descriptions of
everyday events and follow a consistent sequence. Output only the prose.

Example paragraph:
<exact contents of opening.txt>

Continue with another ordinary event from the same day, in the same voice.
```

For the visible-opening version, use a matching continuation instruction and
prefill the assistant turn with the opening followed by the agreed separator.
The prompt-only condition emits its entire cover through the codec; its example
is not automatically copied into the output. The visible opening carries no
encrypted payload bits; coding begins after the separator.

## Controlled comparisons

Phase 1 compares four conditions under the same source compression policy:

| Condition | Prompt | Temperature |
| --- | --- | ---: |
| Existing control | Existing `varied` | 1.0 |
| Existing control | Existing `warm` | 1.2 |
| Proposed style example | Generic instruction plus fixed library paragraph | 1.0 |
| Proposed style example | Same instruction and paragraph | 1.2 |

Use the key-message, belfry, and paragraph payloads from `compact_demo.py`.
Run ten independent encryptions per payload and condition: 120 completed round
trips if all attempts succeed. Preserve every attempt and record failures.
Interleave conditions to reduce ordering effects. Random nonces mean the covers
are independent trials, rather than matched token paths.

Keep the existing model hash, runtime, CPU settings, top-64 candidates,
prefix-free selection, context policy, completion rule, and `auto` source coding.
Record the implementation commit and literal prompts before running. Add new
profile names for the proposed conditions; preserve the existing profiles so
old covers can still be decoded. The current runner does not implement these
conditions; extend it in the experiment's implementation commit.

Phase 2 adds visible openings at 1.0 and 1.2 if phase 1 improves readability.
Run the same payloads and repetition count. Initially use the fixed library
opening, then check a second topic before claiming the approach generalizes.
Keep results from each phase separate.

## Protocol work for a visible opening

Before implementing arbitrary per-message openings, specify these details:

- Accept one nonempty UTF-8 paragraph without protocol control markers or line
  breaks. Preserve its bytes; perform no whitespace or Unicode normalization.
  Emit it followed by exactly `\n\n`. The first such separator is the boundary
  between the public opening and encoded continuation. Reject malformed input.
- Tokenize the public opening as ordinary text with special-token parsing off.
  Define how its tokens join the fixed assistant prefix and remain in context.
  Both sides reconstruct this identically; budget the fixed prompt, opening,
  and rolling history within the 2048-token server context. Set an explicit
  opening limit and reject oversized openings before inference.
- Bind a digest of the opening and the full prompt/configuration to key
  derivation and frame authentication in a separately named protocol variant.
  The receiver reads the opening before deriving the context-dependent keys.
  A changed opening must fail without writing plaintext.
- Keep the opening outside the arithmetic payload history. The decoder strips
  exactly the agreed prefix and decodes the continuation with that prefix in
  the model context. It must need only the cover, key, and shared implementation,
  with no per-message prompt file or encoder statistics.

Merely adding a paragraph to the encoder's prompt would break replay when the
decoder does not have it. The visible-prefix rule resolves that dependency.
This is a proposal for a new variant; it is not implemented by compact v2 today.

## Measurements and acceptance

For every trial, retain input, opening/prompt, exact cover, recovered bytes,
encoder/decoder statistics, logs, and hashes under `runs/<unique-run-id>/`.
Report full cover bytes, opening bytes, continuation bytes, compression choice,
frame bytes, token counts, entropy, sentence-completion overhead, and timings.
For one-line inputs, report absolute overhead as well as expansion ratios.

Have a reader rate the generated continuation in shuffled, unlabeled order
for coherence, ordinary language, consistency of voice, and continuity from the
opening on a 1–5 scale. Show the supplied example separately for voice judgments;
exclude its copied text from the continuation score. Retain the ratings and
flag concrete problems such as tense shifts, invented compounds, and incomplete
sentences. Record who rated the samples and whether they were machine ratings;
do not describe machine ratings as a human study.

Require exact recovery for every claimed success and no plaintext output for
wrong-key, wrong-profile, modified, truncated, or appended covers. For phase 2,
also test altered openings, malformed separators, excessive opening lengths,
and fresh-server decoding. Unit tests must cover prefix handling and binding.

A useful result improves the median continuation ratings versus the current
warm control and reduces concrete prose failures on this fixture. Report size
and timing costs alongside it. There is no preselected size win or justification
for a statistical-security claim. A single successful topic remains a pilot.

## Closeout

Replace this plan's status with the actual outcome. Link raw results, readable
examples, failures, ratings, and implementation/evidence commits. State whether
the prompt example or public opening is worth keeping and what remains lacking.
Update [Experiments and directions](../../EXPERIMENTS.md) with a short result.

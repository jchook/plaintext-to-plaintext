# 003: Opening-paragraph steering

Status: implementation ready; pilot pending. Proposed on 2026-10-21 after the
[compact v2 trial](../002-compact-v2/README.md). The separately named opening v1
codec and runner are implemented; see [PROTOCOL.md](PROTOCOL.md) for commands and
the exact context and framing rules. No measured improvement is claimed yet.

## Question and design decision

Can a supplied public first paragraph set the subject, voice, and format of the
whole cover while preserving exact recovery? The current unfamiliar-town prompt
and temperature of 1.2 sometimes produce an exaggerated travel narrative. The
[saved paragraph cover](../002-compact-v2/runs/main/paragraph.warm-auto.1.cover.txt)
is one example. Prompt, temperature, model size, and candidate filtering may each
affect readability; this experiment does not assume a cause in advance.

The user's clarified design is one fixed, versioned prompt template containing
`{{opening_paragraph}}`. The sender supplies a public opening as a separate input.
The template wraps that paragraph with instructions to continue the same kind
of message. The transmitted cover starts with the exact opening, followed by
the generated continuation that carries the encrypted frame.

The same opening therefore serves two purposes: it supplies model context and
travels with the cover so the decoder can reconstruct that context. A dropdown,
free-text field, or separate LLM can produce it. The decoder does not need to
know which method the sender used, or share a catalog of standard openings.

On 2026-10-21, this clarification replaced the earlier proposal to test a fixed
style example first and add a visible opening later. The primary experiment now
uses both parts together. A prompt-only comparison can be a later ablation.

## Fixed template and variable opening

The proposed [prompt template v1](prompt-template-v1.txt) contains one replacement
slot. It instructs the model to match the opening's purpose, point of view, and
level of formality, then produce only the continuation. It asks for an email
continuation when the opening is an email, rather than forcing every fixture
into a journal entry. Keep the wrapper identical across topics.

Conceptually:

```text
prompt = render(template_version, opening_paragraph)
cover = opening_paragraph + "\n\n" + encode_frame(prompt, encrypted_frame)
```

The decoder reads the first paragraph from the cover, renders the same template,
and decodes the remaining text. The opening carries no encrypted payload bits.
The secret input is encoded in full and must be restored byte-for-byte.

The proposed template quotes the opening in the user instruction and requests
the next paragraph. Initially leave the assistant turn empty, matching the
existing predictor's context structure. Prefilling the assistant turn as well
is a separate possible ablation; specify its exact tokenization before testing.

The paragraph is public cover material, independent of the private payload.
An automatic opening generator should receive cover preferences such as genre
or topic. Save its exact output as the opening; the decoder must never need to
rerun that generator or receive its prompt. Template and protocol versions remain
shared dependencies, while opening text varies for every message if desired.

## Opening fixtures

All fixtures are one UTF-8 paragraph without a trailing line break. Names and
situations in these examples are fictional.

| Fixture | Purpose | What to inspect in the continuation |
| --- | --- | --- |
| [Conference follow-up](openings/conference-followup.txt) | Friendly professional email with Shannon arranging a product meeting | Consistent roles, ordinary follow-up, no invented meeting dates or agreements |
| [STEM revision note](openings/stem-revision.txt) | Email about revising a statistical-model explanation | Coherent discussion of revisions without fabricated measurements or citations |
| [History revision note](openings/history-revision.txt) | Email about the direction of a chapter on trade and port cities | Consistent editorial discussion without invented historical evidence |
| [Project update](openings/project-update.txt) | Brief progress report about a neighborhood website | Concrete next steps without excessive new scope or unsupported commitments |
| [Hobby planning](openings/hobby-planning.txt) | Casual email planning a photography walk | Everyday voice and continuity without invented logistics |
| [Library update](opening.txt) | The original personal-update fixture | Generalization beyond professional correspondence |

Start with the first three requested concepts. The others are follow-up topics.
Writing-feedback messages are useful because the continuation can discuss
structure, clarity, or questions for the reader without needing an actual paper
or a large set of externally checked facts. Evaluate topical accuracy separately
if a later fixture asks for substantive STEM or history exposition.

## Pilot and controlled comparisons

Use the conference, STEM, and history openings at temperatures 1.0 and 1.2.
Use the key-message and paragraph payloads from `compact_demo.py`, with two
independent encryptions per combination: 24 seeded trials. Add the existing
`varied` and `warm` controls with the same two payloads and repetition count:
eight control trials. The first pilot therefore attempts 32 round trips.

Keep model hash, runtime, CPU settings, top-64 candidates, prefix-free selection,
context policy, completion rule, and `auto` source coding unchanged. Record the
implementation commit and exact rendered prompts. Interleave conditions and
retain failures. Independent nonces yield different token paths, so these are
not paired covers with identical randomness.

The opening v1 implementation and runner preserve the existing v1/v2 profiles
for old covers. Checkpoint the implementation before collecting data. After inspecting the pilot,
record any template changes under a new version before a larger comparison.
Do not combine results from different wrappers into one condition.

If the pilot is promising, add the belfry payload and increase to ten encryptions
per opening, temperature, and payload. Across the three initial openings and two
unseeded controls, that larger comparison has 240 trials. Test additional topics
before claiming that the wrapper works broadly.

## Protocol details to settle before implementation

- Accept one nonempty UTF-8 paragraph without line breaks, reserved template
  delimiters, or model control markers. Preserve its bytes without whitespace
  or Unicode normalization. Emit exactly `opening + "\n\n" + continuation`.
  The first blank line is the decoding boundary. Reject malformed inputs.
- Render the single placeholder once as literal text. Tokenize opening content
  without interpreting special model tokens. Version the complete wrapper,
  chat formatting, temperature, candidate rules, and context policy.
- Budget the rendered prompt and rolling history within the 2048-token server
  context. Set an explicit opening-token limit and reject oversized openings
  before scoring. Keep the opening in the fixed prompt as history rolls forward.
- Bind the exact opening and full configuration to key derivation and frame
  authentication under the new protocol. Changing the public opening must fail
  without writing plaintext, even if the rest of the cover is unchanged.
- Keep the opening outside arithmetic payload history and sentence-completion
  accounting. Decode the continuation using the reconstructed fixed prompt.
  No per-message sidecar, preset ID, or encoder statistics may be required.

The cover carries the variable public input; the shared template supplies the
structure around it. Arbitrary opening text is not an arbitrary per-message
change to the shared protocol.

## Measurements and acceptance

Retain the opening, template version, rendered prompt, input, exact cover,
recovered bytes, statistics, logs, and hashes in each run. Report full cover
bytes, public-opening bytes, continuation bytes, compression choice, frame bytes,
token counts, entropy, completion overhead, and timing. Count the entire opening
in transmitted size even though it carries no payload bits.

Have a reader rate generated continuations in shuffled, unlabeled order for
coherence, ordinary language, voice consistency, and continuity from the opening
on a 1–5 scale. Show the opening for context but exclude copied opening text from
the score. Save ratings and concrete failures: tense shifts, repeated greetings,
role changes, invented compounds, fabricated facts, and unfinished sentences.
Identify the rater and distinguish human assessments from machine assessments.

Require exact recovery for every claimed success and no plaintext output for
wrong-key, wrong-template, wrong-temperature, modified, truncated, or appended
covers. Test altered openings, malformed separators, excessive opening lengths,
and fresh-server replay. Unit tests must cover template rendering, prefix
handling, and authentication binding.

A promising result improves continuation ratings and reduces concrete prose
failures versus the current warm control. Report any size or speed cost.
Naturalness and resistance to steganalysis remain separate evaluation questions;
the existing repository contains no evidence that a particular email genre is
harder to detect.

## Closeout

Replace the planned status with the actual outcome. Link raw results, readable
examples, failures, ratings, and implementation/evidence commits. Record the
wrapper version kept or rejected and the next question. Update
[Experiments and directions](../../EXPERIMENTS.md) with a short result.

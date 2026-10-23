# Where the successful covers spend their length

Retrospective review, 2026-10-22, from checkout `12628b49e9dfd44105f1beae584878ab2d6c7111`.
No inference or codec changes. [audit.py](audit.py) checks exact source/recovered
bytes for 57 archived successes: four v1, 21 compact trials, and 32 opening-pilot
trials. [audit.json](audit.json) records input hashes and per-cover measurements.
The existing [size audit](../2026-10-22-size-plausibility/README.md) supplies the
earlier entropy and literature context. This review adds visible-byte allocation,
prose-structure counts, and specific examples of text continuing after a plausible
message ending. Qualitative judgments below are an agent review, not human ratings.

The largest opportunity is to carry the required frame in fewer visible bytes.
The public opening is an additional substantial fixed cost. Repeated requests for
feedback make some messages look longer than their purpose warrants, but that
prose mostly still carries encrypted bits. Deleting it would break recovery.

## Accounting at temperature 1.2

Each column pools six opening-pilot trials: three fixtures, two repetitions each.

| Component or rate | 16-byte input | 238-byte input |
| --- | ---: | ---: |
| Complete cover | 1,297.2 B | 1,824.5 B |
| Public opening and separator | 375 B | 375 B |
| Prose carrying the encrypted frame | 834.2 B | 1,415.8 B |
| Deterministic sentence ending | 88 B | 33.7 B |
| Packed source | 17 B | 49 B |
| Encrypted frame | 47 B | 79 B |
| Frame bits / carrying visible byte, pooled | 0.451 | 0.446 |
| Packed-source bits / complete visible byte, pooled | 0.105 | 0.215 |
| Original-input bits / complete visible byte, pooled | 0.099 | 1.044 |

Original-input bit counts are byte lengths, not estimates of independent secret
information. The paragraph's high original-input rate includes its successful
compression. Packed-source and frame rates measure different layers and should
remain separately labeled.

At these carrying rates, one frame byte requires approximately 18 visible bytes.
The 30-byte outer frame overhead therefore accounts for roughly **532–538 visible
bytes** at the observed rate. This allocates carrying cost proportionally; it
does not predict a re-encoding after changing the frame. Different encrypted bits
produce different language histories and rates.

The 30 bytes comprise a 12-byte nonce, two length bytes, and a 16-byte
authentication tag. They are requirements of the current protocol, not disposable
padding. Amortizing them over multiple secrets in one transmission is a possible
application choice. Reducing them requires a separately specified protocol.

The paragraph's 49-byte packed source comprises 29 bytes of arithmetic-coded
source plus 20 bytes of type, lengths, and validation. Its 16-byte restored-source
digest alone has a proportional carrying allocation of about **287 visible
bytes**. This digest protects against a genuine additional failure: an inference
runtime disagreement can restore the wrong source from correctly authenticated
compressed bytes. Outer authentication does not by itself check those restored
bytes. See [source_codec.py](../../poc/source_codec.py), `compress_model` and
`decompress_model`. This identifies a cost to investigate, not a recommendation
to remove validation.

## Apparent filler versus bytes that carry no payload

The [history cover](../../experiments/003-opening-paragraph/runs/pilot-20261021/paragraph.opening-history-revision-t1.0.1.cover.txt)
has seven generated paragraphs. Its paragraph beginning “Let me know of any
suggestions” reads like a close, but two more questions follow. Those final
paragraphs occupy 435 visible bytes: **415 carrying bytes and 20 ending bytes**.
They cannot be deleted from the existing cover. A new encoder must carry the
same frame in less space before it can stop there.

The longest opening-pilot cover is the
[conference continuation](../../experiments/003-opening-paragraph/runs/pilot-20261021/paragraph.opening-conference-followup-t1.0.2.cover.txt):
2,973 bytes, six generated paragraphs, and eight question marks. It revisits
feedback, product usability, and simplicity versus complexity. Even after the
paragraph beginning “So far, the feedback”, another 695 bytes follow, of which
660 carry the frame and only 35 are the completion suffix. Unsupported claims
about positive feedback and proposed wireframes also weaken its plausibility.

The [STEM sample](../../experiments/003-opening-paragraph/runs/pilot-20261021/paragraph.opening-stem-revision-t1.0.1.cover.txt)
switches from addressing Priya to discussing her in the third person. The
[warmer STEM sample](../../experiments/003-opening-paragraph/runs/pilot-20261021/paragraph.opening-stem-revision-t1.2.1.cover.txt)
quotes the opening and invents an included revised section. These are concrete
quality defects. The saved aggregates do not establish that their particular
sentences have low embedding rates.

Across all six paragraph openings, mean generated paragraph counts fall from
5.0 at temperature 1.0 to 3.0 at 1.2. Individual covers range from one to seven
paragraphs, so paragraph count is a poor bandwidth unit. Frame bits per visible
byte and full transmitted bytes are more useful.

## Evidence about the bottleneck

For the short input, mean carrying prose falls from 1,270.3 to 834.2 bytes between
temperatures 1.0 and 1.2. For the paragraph it falls from 2,022.2 to 1,415.8 bytes.
Mean visible bytes per carrying token barely change: about 5.03 to 4.97 for the
short input and 5.11 to 5.06 for the paragraph. The observed size change therefore
comes mostly from carrying more bits per token, rather than shorter token pieces.
These are independent random encryptions, not paired paths or causal estimates.

Even within a matched opening/temperature condition, different ciphertexts follow
different language paths. At 1.0 the two history short-message carrying lengths
are 1,822 and 993 bytes for the same 47-byte frame. Whole-run rates alone conceal
where a generation becomes predictable. New per-token traces should record
entropy and expected visible bytes alongside paragraph boundaries.

The ending costs about 2% of the warmer paragraph cover and 7% of the warmer short
cover. It is a secondary target. Arithmetic interval overshoot in the 24 opening
trials ranges from 0.37 to 7.49 bits, under one frame byte. Removing final interval
overshoot alone cannot explain away hundreds of visible bytes.

The compact/v1 prompts request about 1,500 words; the public-opening wrapper
does not. The encoding loop stops when it has represented the frame, then finishes
the sentence. It does not mechanically generate 1,500 words. The old instruction
may alter the distribution toward open-ended narration, but blaming it for the
observed length needs a matched prompt ablation.

## Prioritized hypotheses and tests

| Priority | Hypothesis | Test and evidence against it |
| --- | --- | --- |
| 1 | Shorter public context removes a large cost without sacrificing the continuation. | Compare short and long openings under the same wrapper. Include any increase in carrying prose and blinded quality defects; reject the hypothesis if they consume the saved opening bytes or quality fails. |
| 2 | An adaptive density control can exploit positions with many acceptable alternatives while avoiding costly changes at constrained positions. | Record per-step entropy, expected bytes, and policy distortion. Compare full size and recovery with fixed temperature at several settings. Reject if gains vanish at acceptable plausibility. |
| 3 | Prompt/genre and joint wording/structure choices can expose acceptable alternatives our current local policy seldom reaches. | Compare messages with a clear limited purpose, alternate sentence structures, and a reproducible decoder. Count every plan identifier or auxiliary message. Reject if extra planning bits, narrow continuations, or errors consume the benefit. |
| 4 | Wider candidate support improves recoverable bits per visible byte. | Measure full or wider-support distributions and replay-safe decoding before making claims. Added candidates may be long, implausible, or difficult to distinguish; probability mass alone does not establish gain. |
| 5 | Protocol overhead can be amortized for a useful real workload. | Test batching only if one combined transmission fits the use. Count latency and message-context effects. Preserve exact restored-source verification and authentication, or explicitly specify and evaluate their replacements. |
| 6 | A denser decoder with bounded errors plus error correction beats the exact decoder's net rate. | Measure substitutions, deletions, and synchronization loss under an explicit channel. After adding parity, block framing, and resets, compare recovered secret bits per complete byte. The current exact saved channel has no observed errors for correction to remove. |

For the error-correction hypothesis, if carrying density rises from `d0` to `d1`
bits per visible byte and correction has code rate `r`, its idealized useful rate
is `r*d1`. It improves size only when that exceeds `d0`, after including extra
framing and synchronization costs. This preserves the possibility of a better
channel design; it does not infer a benefit merely from adding parity to the
existing exact codec.

Run the retrospective check from the repository root:

```sh
python3 research/2026-10-22-encoding-density-audit/audit.py --check
```

This verifies the saved records. It does not perform a fresh model replay,
measure per-sentence capacity, or estimate detectability.

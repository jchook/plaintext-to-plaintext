# 005: Five-setting density sweep

Status: completed, 2026-10-22 (local date). Predecessor: [004 plan](../004-size-frontier/README.md).
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

## Results and evidence

All **40/40** scheduled trials completed with authenticated, byte-exact recovery.
There were no failed, interrupted, oversized, or timed-out trials. Every input,
cover, recovered file, prompt, configuration, phase log, and result is retained in
[runs/pilot-20261022](runs/pilot-20261022/). See the audited
[summary](runs/pilot-20261022/summary.json),
[raw results](runs/pilot-20261022/results.json), and
[attempt log](runs/pilot-20261022/attempts.json).

Each temperature has four payloads and two independent repetitions. The table
averages each payload's two runs, then weights the four payloads equally.
Frame bits/token counts encrypted frame bits over carrying continuation tokens;
it differs from original secret bits per full transmitted byte.

| Temperature | Mean full bytes | Range across eight covers | Frame bits/carrying token | Mean machine score /14 | Rubric passes /8 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.8 | 3,435.6 | 2,200–4,175 | 0.991 | 5.625 | 0 |
| 1.0 | 2,459.9 | 1,685–3,688 | 1.492 | 7.750 | 1 |
| 1.2 | 1,802.4 | 1,341–2,246 | 2.301 | 8.625 | 2 |
| 1.4 | 1,420.6 | 1,044–1,568 | 3.106 | 7.875 | 0 |
| 1.6 | 1,206.4 | 955–1,418 | 4.055 | 6.125 | 0 |

These ranges include different payload sizes as well as repetitions. They are
not confidence intervals. Source packing and frame length were identical across
temperatures within each payload, so the size comparison does not mix different
compression choices. Each complete cover includes the same 358-byte public
opening and separator; each frame adds 30 bytes to its packed source.

| Payload | Original bytes | Packed bytes | Frame bytes | Mean full bytes at 1.2 | Mean full bytes at 1.6 | Reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| key-message | 16 | 17 | 47 | 1,353.0 | 1,009.5 | 25.39% |
| paragraph | 238 | 49 | 79 | 1,780.5 | 1,266.0 | 28.90% |
| unicode | 42 | 43 | 73 | 1,998.0 | 1,137.5 | 43.07% |
| binary | 64 | 65 | 95 | 2,078.0 | 1,412.5 | 32.03% |

Moving from 1.2 to 1.6 reduced mean complete cover size by **596 bytes (33.07%)**
in this balanced corpus. It also increased grammatical failures: the reviewer
tagged grammatical collapse in six of eight 1.6 covers. At 0.8, all eight covers
received repetition and excessive-length tags. Temperature 1.2 had the highest
mean score in this pilot; lower temperature did not provide a reliably more
plausible endpoint.

The reviewer scored all forty covers before seeing their temperature or size
mapping. Only three met the frozen composite threshold. All three scored zero
on unsupported claims: that dimension was not a mandatory nonzero gate in the
preregistered rule. A rubric pass therefore does not mean grounded correspondence.
Keep that limitation when interpreting the pass counts.

Across forty covers the machine reviewer tagged invented facts in 38, repetition
in 24, excessive length in 24, unnatural endings in 20, role drift in 19,
grammatical collapse in eight, and prompt leakage in five. Individual dimensions,
notes, and categories remain in the summary and the
[blinded review files](runs/pilot-20261022/blind-review/).

## Secondary ordinary-generation controls

After the sweep we ran the separately declared
[ordinary-generation diagnostic](controls-protocol.md). These five texts contain
no hidden payload and are excluded from density and recovery aggregates.
The [control summary](controls/pilot-20261022/summary.json) links full requests,
raw responses, exact covers, stop metadata, and blind ratings.

| Temperature | Full cover bytes | Generated tokens | Stop | Machine score /14 | Rubric pass |
| --- | ---: | ---: | --- | ---: | --- |
| 0.8 | 1,085 | 138 | eos | 11 | yes |
| 1.0 | 1,806 | 271 | eos | 11 | yes |
| 1.2 | 1,008 | 122 | eos | 13 | yes |
| 1.4 | 1,116 | 136 | eos | 11 | yes |
| 1.6 | 620 | 46 | eos | 8 | no |

All five controls stopped at EOS, with no context truncation or token-limit stop.
Four met the same composite threshold; grounding weaknesses remained. The
reviewer knew this batch was ordinary generation, while temperature stayed
hidden. Thus the comparison is temperature-blinded, not treatment-blinded.

The controls support further investigation of stopping behavior. The codec
suppresses EOS and must continue until it has carried its frame; ordinary
generation can stop earlier. Continuing past a natural ending could explain
some repeated closes, alternate drafts, or writing advice. These five controls
also differ in prefix-free filtering and payload-driven sampling. They do not
isolate the cause or establish failure frequencies.

## Reproducibility, cost, and checks

The measured sweep implementation was committed before inference at
`12628b49e9dfd44105f1beae584878ab2d6c7111`. All eleven measured files match that
commit and the retained source snapshots. The control protocol/runner began at
`030178e`; `83391d0` added the pre-control termination hypothesis and accounting
helpers before any control inference. Both runs used model SHA256
`dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff`
and runtime build `b1-0f3a71be1`.

The sweep took 1,696.93 seconds (28.3 minutes). Its recorded codec calls include
26,494 cover-model completion calls across encoding and decoding, plus 610
source-encoding model calls; source-decoding calls were not instrumented.
The five ordinary controls took 35.12 seconds in total. Inference was local,
with no API charges. CPU electricity was not measured.

Before inference, 39 local tests passed and an existing 003 cover recovered
exactly through the adapter in a separate process. No historical model replays
were added at closeout. The offline archive check passed and compared all 97
saved full round trips byte-for-byte, including this experiment. Visible full
cover and continuation token counts were measured with the pinned tokenizer;
[measurements](runs/pilot-20261022/tokenizer-measurements.json) and individual
rates are retained separately from the carrying-token rate.

The initial sandbox could not bind the server socket. Its
[failed startup log](validation/sandbox-server-failure.log) is retained; approved
execution started the dedicated local server. No model server existed initially.
After the sweep, controls, and token measurements, we verified its PID, exact
command, and process start identity, then stopped that server. It exited zero.
See [validation](validation/) for model/runtime hashes, tests, compatibility
replay, archive check, server identity, startup log, and shutdown record.

Evidence commit: `ea601ac834633b8ae4805487a2c2e07341e3b7bc`. Closeout is committed separately.

## Decision and next question

The experimental temperature control changes density substantially and preserves
exact recovery in this runtime. It does not yet provide a calibrated
plausibility slider. Keep 1.2 as the comparison baseline for the next pilot;
treat 1.4 and 1.6 as denser research settings whose grammar/role failures need
attention. Two runs per payload and one opening are too few to select a stable
production setting.

Test shorter public openings and ways to accommodate natural endings next.
Compare those changes with the current forced-continuation rule before pursuing
a coder replacement. Any segmentation must count repeated openings and framing
against its full byte budget. Adaptive probability control remains a separate candidate once
we can assess acceptable correspondence consistently. Detection, edit tolerance,
cross-runtime recovery, and human quality judgments remain unmeasured here.

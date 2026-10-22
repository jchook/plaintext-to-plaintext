# Opening v1 protocol

This experiment uses [poc/opening.py](../../poc/opening.py), independently of
the preserved v1 and compact v2 profiles. The opening is a public input. The
entire private source is still compressed, encrypted, and encoded in the
continuation.

## Run

Start the dedicated server using the [shared setup](../../poc/README.md).
From the repository root, choose output paths that do not already exist:

```sh
python3 poc/opening.py encode --key poc/keys/alice.txt --opening experiments/003-opening-paragraph/openings/conference-followup.txt --temperature 1.0 --input experiments/001-baseline-v1/examples/key-message.txt --output /tmp/opening.cover.txt --stats /tmp/opening.encode.json
python3 poc/opening.py decode --key poc/keys/alice.txt --temperature 1.0 --input /tmp/opening.cover.txt --output /tmp/opening.recovered --stats /tmp/opening.decode.json
cmp experiments/001-baseline-v1/examples/key-message.txt /tmp/opening.recovered
```

The decoder receives no opening file, token trace, or statistics file. It needs
the shared template/protocol, temperature, exact model/runtime, and key. Its
first scoring request resets the model cache, as in compact v2.

## Context and framing

The sender replaces the single literal slot in
[prompt-template-v1.txt](prompt-template-v1.txt), wrapped in fixed Llama chat
formatting. The opening is tokenized as ordinary text with special-token parsing
disabled. Fixed template segments parse the chat controls. The assistant turn
starts empty; its output is the continuation.

An opening must be nonempty printable UTF-8 without line breaks or reserved
markers. The maximum is 4,096 bytes and 256 model tokens; the complete fixed
prompt is limited to 768 tokens. It stays present while the last 1,024 generated
tokens roll forward inside the 2,048-token server context. Validation preserves
leading/trailing spaces and performs no normalization.

The cover is the exact opening, two newline bytes, and encoded continuation.
The receiver splits at the first blank line. Subsequent paragraph breaks belong
to the continuation. Changing an opening changes both predictor context and keys.

Key derivation and authenticated associated data bind the opening, rendered
prompt, template version/hash, temperature, model hash, tokenization policy,
context policy, and candidate/completion rules under a separate `opening-v1`
domain. The frame retains compact v2's 30-byte overhead and length masking.
Source coding uses the unchanged raw/zlib/LLM automatic selection.

The arithmetic coder and deterministic completion suffix reuse compact v2.
Output bytes are written only after frame authentication, suffix checking, and
exact source restoration. Old v1/v2 cover decoding remains available through
the original scripts.

## Pilot artifacts

```sh
python3 poc/opening_demo.py --directory experiments/003-opening-paragraph/runs/<unique-run-id>
```

Defaults schedule 32 attempts with deterministic interleaving and independent
random encryption nonces. `metadata.json` records commands, source revision,
source hashes and snapshots, settings, and server properties. `attempts.json`
records every scheduled attempt and phase, including failures; `results.json`
contains only authenticated exact-byte round trips.

Each successful attempt retains input, cover, recovered bytes, logs, per-process
statistics, and rendered prompt. Seeded attempts also retain opening and template
files. The saved code snapshot preserves the exact sources used for the run.

`cover_bytes` includes the public opening, separator, and continuation.
`realized_frame_bits_per_cover_byte` uses that complete denominator; the separate
continuation rate excludes the public prefix. Prompt-token and opening-token
counts describe fixed context, while payload-token counts describe encoded bits.

Generate descriptive measurements and mechanically selected samples with:

```sh
python3 experiments/003-opening-paragraph/summarize.py experiments/003-opening-paragraph/runs/<unique-run-id> --output /tmp/opening-summary.json
```

Sample selection uses the paragraph payload, first repetition, and temperature
1.0 for each seeded topic, plus the warm control. It does not select outputs
by their apparent quality. Human or machine assessments must be identified
separately from those descriptive measurements.

## Rejection and restart validation

After the pilot finishes, retain seven separate-process negative checks:

```sh
python3 poc/opening_validate.py --run experiments/003-opening-paragraph/runs/<run-id> --directory experiments/003-opening-paragraph/runs/<run-id>/validation
```

The helper uses the run's source snapshot and checks wrong key, changed opening,
changed continuation, truncation, appended text, wrong temperature, and malformed
prefix. A pass requires a recognized case-specific codec rejection with neither
plaintext nor statistics written. Infrastructure failures, timeouts, and Python
tracebacks fail validation.

After actually stopping and restarting the dedicated server, run:

```sh
python3 poc/opening_validate.py --run experiments/003-opening-paragraph/runs/<run-id> --directory experiments/003-opening-paragraph/runs/<run-id>/restart-validation --restart-check --restart-note '<recorded old and new process identities>'
```

The helper does not restart the server. This second mode checks an opening cover
and the original v1 key-message cover, requiring authenticated, byte-exact
recovery. Runtime logs and process identities must substantiate the restart.

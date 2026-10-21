# 001: Reproducible v1 codec

Status: completed local trial. Code and evidence first committed together in
`ec98261` on 2026-10-18. The [protocol and runtime instructions](PROTOCOL.md)
describe the implementation; [verification.json](verification.json) records the
original validation.

## Question and design

Can a receiver recover arbitrary original bytes using only visible cover text,
the shared key, and a fixed model/protocol? V1 encrypts a padded frame, then
uses exact-integer arithmetic coding over prefix-free printable token pieces.
The decoder reconstructs the probability tables and authenticates the frame
before writing plaintext. It receives no encoder trace or token sidecar.

The recorded model is Llama 3.2 3B Instruct Q4_K_M, SHA-256
`dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff`,
with llama.cpp build `b1-0f3a71be1`, four CPU threads, and no GPU offload.
The prompt is a pleasant-day journal entry at temperature 1.0. The Alice book
in [poc/keys/](../../poc/keys/) is a public demonstration key.

## Results and evidence

| Input | Input bytes | Frame bytes | Cover bytes | Recovery |
| --- | ---: | ---: | ---: | --- |
| Key message | 16 | 64 | 1,608 | Exact |
| Belfry warning | 53 | 96 | 2,635 | Exact |
| Unicode and mixed whitespace | 42 | 96 | 2,718 | Exact |
| Empty | 0 | 32 | 1,317 | Exact |

The [key-message files](examples/) and [remaining three runs](runs/verified/results.json)
retain inputs, covers, restored bytes, and per-process statistics. Encoder and
decoder ran separately. Four recorded rejection checks (wrong key, modified,
truncated, and appended cover) wrote no plaintext. The
[restart result](examples/key-message.after-restart.json) records successful
key-message decoding after restarting the server. Nine local tests passed at
the time; the current shared suite includes additional compact tests.

## Decisions and limitations

The regular Ollama API's cache behavior changed replay probabilities. V1 uses a
dedicated single-slot llama.cpp server, controlled cache resets, and identical
token-ID requests. Prefix-free visible pieces resolve tokenization ambiguity
at the cost of restricting choices. The authentication tag identifies the
frame boundary, and the decoder checks a deterministic completion suffix.

This establishes local recovery under the recorded conditions. It does not
establish statistical invisibility, tolerance of edits, runtime portability,
or phone performance. The 32-byte framing boundary and low-entropy journal
prompt produce substantial expansion, especially on short messages.

The [literature review](../../research/summary.md) motivated measuring entropy
after filtering and trying lossless compression before encryption. The next
[compact experiment](../002-compact-v2/README.md) addresses those costs while
retaining the v1 implementation for comparison.

## Reproduction

From the repository root, start the server using [PROTOCOL.md](PROTOCOL.md), then:

```sh
python3 poc/demo.py --directory experiments/001-baseline-v1/runs/<unique-run-id>
```

Replace `<unique-run-id>` with a new name. This is a reproduction recipe;
the original launch commands were not archived as shell history. Saved JSON
contains the inference identities and measured results.

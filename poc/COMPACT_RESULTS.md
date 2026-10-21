# Compact codec: local experiment

The compact codec roughly halved the cover size for the short messages in this
trial. A 238-byte English paragraph became 1,104–1,164 bytes of cover, or about
4.6–4.9 times its original size. Every completed round trip recovered the exact
original bytes. This remains an experiment: tiny messages still expand heavily,
and the warmer cover distribution sometimes produces conspicuously odd prose.

## Setup

The model was the existing Llama 3.2 3B Instruct Q4_K_M GGUF, SHA-256
`dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff`,
served by the pinned llama.cpp build `b1-0f3a71be1` on four CPU threads. Each
encoder and decoder ran in a separate process. The decoder received the cover
file, Alice key file, and shared codec/profile; it did not receive encoder traces
or statistics. Each row below contains two independently randomized encryptions.

The [implementation notes](COMPACT.md) give the commands and format details.
The original v1 codec remains available through `p2p.py`.

## End-to-end sizes

These results use the `warm` profile and automatic source compression. All sizes
are bytes, including UTF-8 encoding, framing, and the cover's completion suffix.

| Input | Original | Packed source | Encrypted frame | Cover, run 1 | Cover, run 2 | Exact recovery |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `The key is 12345` | 16 | 17, raw | 47 | 775 | 827 | Both |
| Belfry warning | 53 | 36, LLM | 66 | 1,350 | 1,166 | Both |
| English paragraph | 238 | 49, LLM | 79 | 1,104 | 1,164 | Both |
| Unicode and mixed whitespace | 42 | 43, raw | 73 | 1,252 | 1,401 | Both |
| Binary bytes | 64 | 65, raw | 95 | 1,655 | 1,530 | Both |
| Empty input | 0 | 1, raw | 31 | 746 | 575 | Both |

The saved original key-message cover was 1,608 bytes. The new runs were 49–52%
smaller, but still about 48–52 times the source size. This comparison uses the
single saved v1 example, rather than a new pair of v1 key-message trials.

Inspect an actual [paragraph cover](runs/compact-v2-main/paragraph.warm-auto.1.cover.txt)
and its [original input](runs/compact-v2-main/paragraph.warm-auto.1.input).
Full measurements and hashes are in
[the text runs](runs/compact-v2-main/results.json) and
[the Unicode, binary, and empty-input runs](runs/compact-v2-edge-cases/results.json).

## What the separate changes contributed

The same 53-byte warning was tested with successive changes. These are independent
random covers, not matched token paths.

| Variant | Frame | Cover, run 1 | Cover, run 2 | Mean cover |
| --- | ---: | ---: | ---: | ---: |
| Original v1 | 96 | 2,608 | 2,498 | 2,553 |
| V2 framing, original journal, raw source | 84 | 2,397 | 1,980 | 2,188.5 |
| V2 framing, varied prompt, raw source | 84 | 1,518 | 2,001 | 1,759.5 |
| Varied prompt at temperature 1.2, raw source | 84 | 1,066 | 1,205 | 1,135.5 |
| Same temperature, automatic source compression | 66 | 1,350 | 1,166 | 1,258 |

The full compact pipeline's mean cover was 50.7% smaller than v1 in these runs.
Removing padding reduced the frame from 96 to 84 bytes. Source compression reduced
it further to 66 bytes. Changing the prompt and temperature increased the available
cover choices without changing the raw frame size.

Crucially, the two compressed covers were longer on average than the two warm raw
covers, despite carrying a smaller frame. The passages followed different paths
with different conditional entropies. Two samples are insufficient to estimate a
stable benefit for each change; the compressed frame reduction is exact, while
the realized prose-length reduction is variable. These results should not be
presented as a monotonic improvement across every row.

[All ablation inputs, covers, timings, and hashes](runs/compact-v2-ablation/results.json)
are retained.

A further [paragraph comparison](runs/compact-v2-paragraph-baseline/results.json)
used the same warm cover profile with raw source. Its 269-byte frame produced
2,947 bytes of cover and recovered exactly. Source compression reduced the frame
to 79 bytes and the observed covers to 1,104 and 1,164 bytes: 60.5–62.5% less cover
than that uncompressed run. Encoding took 37.0 seconds for the raw run versus
17.2 and 17.6 seconds for the compressed runs, including source compression.
This is one raw baseline against two compressed runs, not a statistical estimate.

## Source compression and remaining overhead

Automatic mode compared complete source representations, including type bytes,
lengths, and the LLM representation's 16-byte source-integrity digest:

| Source | Raw representation | zlib representation | LLM representation | Selected |
| --- | ---: | ---: | ---: | --- |
| Key message | 17 | 25 | 25 | Raw |
| Warning | 54 | 59 | 36 | LLM |
| Paragraph | 239 | 160 | 49 | LLM |

For the paragraph, the arithmetic-coded source itself occupies 29 bytes. Its
headers and digest bring that to 49 bytes; encryption and frame length add another
30 bytes. The result is a 79-byte frame. The model compression is lossless token
coding with literal escapes, not a summary or semantic reconstruction.

Across the six main text runs, the unweighted mean frame rate was 2.29 bits per
payload token and the mean integer-table entropy was 2.34 bits per token. Before
prefix-free filtering, the mean conditional top-64 entropy was 2.50 bits; after
filtering it was 2.33 bits. The measured arithmetic rate was already close to the
available entropy. These averages describe sampled paths, not a proof of universal
coding efficiency or full-vocabulary capacity.

The mean expected entropy per visible byte was about 0.52 bits across those six
runs. Increasing that capacity while keeping the prose natural, and amortizing
fixed overhead over longer inputs, remain the main opportunities. The key-message
results demonstrate why source compression alone cannot fix tiny-message expansion.

## Fidelity and limitations

The local suite passes 22 tests covering both protocols, arbitrary source bytes,
token escapes, high token IDs, source-integrity checks, frame tampering, malformed
compressed data, and fallback behavior. The original model-scoring attempt for the
Unicode sample encountered a server content-parser error. Automatic mode now
records that specific limitation and chooses raw or DEFLATE; both subsequent
Unicode round trips preserved the original bytes exactly. Forced LLM compression
still reports an error for that source. Other server errors remain fatal.

Five [real-model rejection checks](runs/compact-v2-rejections/results.json) passed:
wrong key, wrong profile, modified cover, truncated cover, and appended text. None
wrote recovered plaintext.

There were 21 completed end-to-end round trips: twelve default compact runs,
eight ablation runs, and one additional paragraph baseline. After restarting the
dedicated server, a saved LLM-compressed paragraph and the original v1 key-message
cover also [decoded exactly](runs/compact-v2-restart/results.json). The
[verification record](compact-verification.json) includes artifact hashes.

Readability is not uniform. One short warm cover contains “skatedown sun” and
“scalded knee.” The existing punctuation-based completion rule can also stop at an
abbreviation such as “Mrs.” or “Est.” These outputs decode correctly, but they do
not satisfy a strict naturalness requirement. Lower temperature remains available;
no human-rated naturalness study or statistical detectability evaluation was run.

This was a small, hand-selected local test set, not a broad compression benchmark.
Phone performance and cross-runtime interoperability remain untested.

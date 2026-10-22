# Research findings for the plaintext-to-plaintext POC

Follow-up, October 22: [size, plausibility, and detection](2026-10-22-size-plausibility/README.md)
applies this literature to the opening-paragraph pilot, with reproducible byte
accounting and a staged plan for smaller covers. The review below records the
earlier October 18 findings, including its then-current framing assumptions.

Reviewed October 18, 2026, through three research tracks: recent steganographic
methods, coding theory, and practical implementations. These are literature and
documentation findings; we did not reproduce the papers' experiments.

Our pretrained-model-plus-arithmetic-coding construction has direct precedent in
[Neural Linguistic Steganography](2019-neural-linguistic-steganography/relevance.md).
Modern work improves the security analysis, coding overhead, and reliability of
the text channel. There is no single winner across capacity, speed, exact
recovery, edit tolerance, and compatibility between devices.

The most relevant sampler results are
[RRC](2026-rrc/relevance.md),
[SparSamp](2025-sparsamp/relevance.md), and
[ANStega](2026-anstega/relevance.md). They approach the available token entropy
under their respective settings. ANStega includes experiments near our model-size
target: 3.69 hidden bits/token on Qwen2.5-3B and 4.67 on Phi-2 2.7B, with full
vocabulary sampling. Its final ANS state is an additional decoding dependency
that a complete transmission protocol must handle.

RRC's matched comparison on Llama-2-7B is more informative than comparing headline
numbers from unrelated experiments:

| Method | Hidden bits/token | Embedding bits/second |
| --- | ---: | ---: |
| Sorted Discop | 3.33 | 26.13 |
| SparSamp | 3.38 | 326.12 |
| RRC | 3.57 | 146.24 |

These are GPU measurements from [RRC Table 5](2026-rrc/paper.pdf), not phone
benchmarks. The capacity gain over SparSamp is modest, and SparSamp is faster in
this comparison. RRC's near-100% entropy utilization is an empirical result,
not a rigorous capacity-optimality theorem.

Exact recovery from token IDs does not establish exact recovery from visible
text. The [RRC repository snapshot](2026-rrc/upstream-readme.md) reports 100%
recovery from IDs versus about 91% after retokenizing text in one 128-bit
Llama-2-7B experiment. It also records failures after changes to batching and
inference execution. This supports the need for our explicit runtime profile.

[SyncPool](2024-syncpool/relevance.md) preserves the token distribution while
resolving ambiguous token pieces, at a capacity cost.
[Stepwise verification](2025-stepwise-token-verification/relevance.md) is a
practical alternative to our broad prefix-free restriction, with some
distributional change. [Look-ahead Sync](2025-look-ahead-sync/relevance.md) reports
higher capacity than SyncPool in a matched experiment, but requires additional
model calls. [ReTokSync](2026-retoksync/relevance.md) limits desynchronization;
its headline accuracy measures bits, and its exact-recovery demonstration uses
additional correction messages.

Our observed 1.3 frame bits/token is not enough to conclude that the arithmetic
coder wastes entropy. We must measure the entropy of the actual distribution
after prompting, truncation, and candidate filtering. Retained probability mass
alone does not measure retained entropy. A more efficient coder can use more of
that entropy, but cannot create additional choices in the same distribution.

Our own approximate accounting is:

```text
cover bytes / original bytes
    = (frame bytes / original bytes)
      * (8 * cover bytes/token / effective frame bits/token)
```

With the existing 96-byte frame, a hypothetical rate of 4 bits/token and 4.5
visible bytes/token gives about 864 cover bytes, or 16 times the 53-byte original,
before sentence completion. This is an illustration, not a measured improvement.

Two other research directions target different sources of expansion.
[OD-Stega](2026-od-stega/relevance.md) increases available entropy within a
chosen divergence budget. [StegoZip](2025-stegozip/relevance.md) compresses the
secret before embedding and reports about 2.5 times the payload of its baselines.
Its restoration model and explicit corrections are additional components;
semantic similarity alone would not satisfy our byte-exact requirement.

[Weak-asymmetry research](2026-weak-asymmetry/relevance.md) explores decoding
with partial information such as token rankings, which may tolerate some
numerical differences. [Adaptive dynamic sampling](2026-adaptive-dynamic-sampling/relevance.md)
removes the need to expose probabilities but still requires reproducible seeded
sampling. [HiTMS](2026-hitms/relevance.md) improves throughput through batching
and multiple streams; it does not establish a corresponding reduction in total
cover size.

For covers subject to editing, [STEAD](2025-stead/relevance.md) and
[TE-CSA](2026-te-csa/relevance.md) investigate diffusion models. TE-CSA's October
2026 result reports 1.84 bits/token in its setting. This is a separate model and
channel design from our autoregressive Llama implementation.

Security claims usually concern resemblance to ordinary output from the agreed
generator. Resemblance to human correspondence, resistance to editing, and
cross-device numerical compatibility require separate evidence. The
[survey](2026-survey/relevance.md) is a useful map of these distinctions.

The next controlled comparison should measure entropy before and after filtering,
then compare our coder with modern baselines under the same model, prompt, and
runtime. It should report complete cover bytes per recovered input byte, including
authentication, framing, sentence completion, and any extra state or correction
traffic. Lossless source compression should be evaluated before encryption.
Every claimed success should include a comparison of the original and recovered
bytes.

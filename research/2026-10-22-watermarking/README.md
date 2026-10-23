# Sampling steganography and data carrying watermarks

Reviewed through 22 October 2026. This follow-up connects the project's existing
linguistic steganography archive to image, video, and multi-bit text watermarking.

Text can carry another text as a recoverable watermark. The payload becomes bits;
the encoder uses those bits to choose among plausible tokens or rewrites. The
closest adjacent literature studies **multi-bit watermarking**, **distribution
preserving sampling**, and **pseudorandom error-correcting codes**. A detector that
only answers whether a watermark exists does not establish this capability.

Video watermarking contributes methods for surviving damage: embed evidence
across many locations, combine uncertain observations, and design for a specified
transformation channel. Its success does not imply extreme payload compression.
Robust methods often spread a small payload across a large carrier. Transferring
that design to text trades payload density for recovery after edits.

For this codec, the useful additions are the PRC papers, ArcMark, MirrorMark,
CertMark, SimpleMark, and sentence-level paraphrasing watermarks. They suggest a
second research branch for edit tolerance alongside the existing work on smaller,
exactly replayed covers. No new codec or model trial accompanies this review.

## Likely matches for the remembered survey

The description does not identify the paper uniquely. Two strong matches are:

| Paper | Dates | Relevant passage |
| --- | --- | --- |
| [SoK: Watermarking for AI-Generated Content](https://arxiv.org/abs/2411.18479) | November 2024 preprint; IEEE S&P 2025; reviewed June 2025 v3 | Section 3.5 distinguishes message embedding from detection. Section 6.2 discusses Gaussian Shading and PRC image watermarks. |
| [Secure and Robust Watermarking for AI-generated Images: A Comprehensive Survey](https://arxiv.org/abs/2510.02384) | September 2025; reviewed March 2026 v2 | Sections 4.4.3, 5.2, and 7 cover keyed noise sampling, capacity, redundancy, and cryptography. The more recent image-specific candidate. |

If the remembered result involved different messages in separate image regions,
the likely method is [Watermark Anything with Localized Messages](https://arxiv.org/abs/2411.07231),
an ICLR 2025 paper rather than a survey. It reports distinct 32-bit messages
recovered from small regions, with fewer than one bit error in its stated
setting. That is localization evidence, not guaranteed exact message recovery.

## Historical development

Dates distinguish preprints from later publication when relevant. Linked primary
sources support the descriptions. Older direct steganography papers also have
annotations in the existing archive.

### Foundations through 2021

| Date | Work | Contribution |
| --- | --- | --- |
| 1998 | [Cachin, An Information-Theoretic Model for Steganography](https://doi.org/10.1007/3-540-49380-8_21) | Defines concealment through hypothesis testing and relative entropy between cover and stegotext distributions. Fluent text alone is insufficient evidence. |
| 2002 | [Hopper, Langford, and von Ahn, Provably Secure Steganography](https://eprint.iacr.org/2002/137) | Gives computational indistinguishability definitions and constructions from one-way functions. An early basis for sampling an innocent channel while carrying a secret. |
| 2018 | [HiDDeN: Hiding Data With Deep Networks](https://arxiv.org/abs/1807.09937) | Jointly learns an image embedder and decoder through noise, crop, and compression transformations. A precursor to learning text encoders through an edit channel. |
| 2019 | [Neural Linguistic Steganography](https://aclanthology.org/D19-1115/) | Direct precedent for our arithmetic-coded token choices. [Local note](../2019-neural-linguistic-steganography/relevance.md). |
| 2020 | [StegaStamp: Invisible Hyperlinks in Physical Photographs](https://www.matthewtancik.com/stegastamp) | Arbitrary hyperlink bitstrings survive print and photography. The prototype retrieves 56 payload bits after error correction; the linked resource can be much larger than the watermark. |
| 2021 | [Meteor: Cryptographically Secure Steganography for Realistic Distributions](https://www.cs.umd.edu/users/kaptchuk/publications/ccs21_meteor.pdf) | Addresses uneven, realistic token distributions with cryptographic analysis. [Local note](../2021-meteor/relevance.md). |

### The 2023 and 2024 convergence

| Date | Work | Contribution and boundary |
| --- | --- | --- |
| 2022 preprint; ICLR 2023 | [Perfectly Secure Steganography Using Minimum Entropy Coupling](https://arxiv.org/abs/2210.14889) | Couples payloads with cover symbols while preserving the cover marginal. Minimizing joint entropy increases information carried by a sample. [Local note](../2023-minimum-entropy-coupling/relevance.md). |
| ICML 2023 | [A Watermark for Large Language Models](https://arxiv.org/abs/2301.10226) | Secret vocabulary partitions and selected logit boosts. A foundational detection baseline; the original construction is not a general arbitrary-payload codec. |
| 2023 preprint; COLT 2024 | [Undetectable Watermarks for Language Models](https://arxiv.org/abs/2306.09194) | Defines computational concealment against adaptive queries and constructs watermarks under standard assumptions. |
| 2023 preprint; TMLR 2024 | [Robust Distortion-free Watermarks for Language Models](https://arxiv.org/abs/2307.15593) | Uses inverse-transform and exponential-minimum sampling with keyed randomness and alignment-based detection. Directly exploits sampling values, but detection robustness differs from payload recovery. |
| 2023 preprint | [Unbiased Watermark for Large Language Models](https://arxiv.org/abs/2310.10669) | Develops distribution-preserving watermark reweighting. Check what randomness the preservation claim averages over. |
| 2023 preprint; revised 2024 | [Towards Codable Watermarking for Injecting Multi-bits Information to LLMs](https://arxiv.org/abs/2307.15992) | Formalizes customizable payloads and evaluates coding rate and recovery. Balance-Marking uses probability-balanced vocabulary partitions. |
| February 2024 | [Multi-Bit Distortion-Free Watermarking for Large Language Models](https://arxiv.org/abs/2402.16578) | Distribution Interval Shift Coding extends sampling watermarks to recoverable metadata. Directly relevant to manipulating intervals. |
| NAACL 2024 | [Advancing Beyond Identification: Multi-bit Watermark for Large Language Models](https://aclanthology.org/2024.naacl-long.224/) | Multi-bit messages without fine-tuning, with extraction independent of the generating model. A practical payload baseline. |
| NAACL 2024 | [SemStamp](https://aclanthology.org/2024.naacl-long.226/) | Sentence embeddings, locality-sensitive hashing, and rejection sampling improve paraphrase-resistant detection. A relevant representation, not an established high-rate payload channel. |
| CRYPTO 2024 | [Pseudorandom Error-Correcting Codes](https://arxiv.org/abs/2402.09370) | Codewords look random but permit keyed recovery after corruption. Includes a direct constant-rate, stateless steganography application under its assumptions. |
| NeurIPS 2024 | [Edit Distance Robust Watermarks via Indexing Pseudorandom Codes](https://arxiv.org/abs/2406.02633) | Handles insertions, deletions, and substitutions. Alphabet and security-parameter assumptions matter for practical tokenizers. |
| Nature 2024 | [Scalable watermarking for identifying large language model outputs](https://www.nature.com/articles/s41586-024-08025-4) | SynthID-Text uses tournament sampling and evaluates quality at scale. Its main objective is provenance detection. |

### Visual methods that carry messages

| Date | Work | What transfers to text |
| --- | --- | --- |
| ICCV 2023 | [The Stable Signature](https://arxiv.org/abs/2303.15435) | Fine-tunes an image generator's decoder to emit a recoverable binary signature. A persistent model signature differs from fresh per-message ciphertext. |
| NeurIPS 2023 | [Tree-Ring Watermarks](https://arxiv.org/abs/2305.20030) | Structures initial diffusion noise and retrieves it through inversion. Establishes a sampling-noise approach; fingerprints need separate concealment analysis. |
| CVPR 2024 | [Gaussian Shading](https://arxiv.org/abs/2404.04956) | Maps randomized watermark bits into Gaussian latent sampling. A clear analogue of feeding encrypted bits into an LLM sampler. |
| 2024 preprint; ICLR 2025 | [An Undetectable Watermark for Generative Image Models](https://arxiv.org/abs/2410.07369) | PRCs select diffusion latents. Reports 512-bit message recovery under tested attacks and up to 2,500 bits without removal attacks. Image results do not predict text capacity. |
| ICLR 2025 | [Watermark Anything with Localized Messages](https://arxiv.org/abs/2411.07231) | Recovers messages locally from spliced regions. Suggests independently decodable text segments. |
| 2025 preprint | [Gaussian Shading++](https://arxiv.org/abs/2504.15026) | Adds PRC-protected seed transport and soft decoding for repeated use and varying generation settings. Seed management is part of the protocol. |
| December 2024 | [Video Seal: Open and Efficient Video Watermarking](https://arxiv.org/abs/2412.09492) | Trains through video transformations and aggregates soft predictions across frames. The reviewed paper uses 96-bit messages by default; later repository models have different capacities. |
| ICLR 2025 | [VideoShield](https://arxiv.org/abs/2501.14195) | Maps bits into video diffusion noise, recovers through inversion, and localizes spatial and temporal tampering. Relevant to sampling and synchronization. |
| September 2026 preprint | [COVER: Codec-Robust Video Watermarking with Generative Video Priors](https://arxiv.org/abs/2609.26236) | Embeds and recovers in video-autoencoder latent space, training through codec surrogates. Supports designing for the actual damage channel, but supplies no ready-made text representation. |

### Message recovery and coding in 2025 and 2026

| Date | Work | Contribution and boundary |
| --- | --- | --- |
| 2025 preprint | [Distributional Information Embedding: A Framework for Multi-bit Watermarking](https://arxiv.org/abs/2501.16558) | Analyzes information rate, quality, and detectability. Distinguish its asymptotic and finite-token settings. |
| ICML 2025 | [StealthInk](https://arxiv.org/abs/2506.05502) | Multi-bit provenance through distribution-preserving sampling, with model-free extraction. More directly relevant than presence-only watermarking. |
| 2024 preprint; USENIX Security 2025 | [Provably Robust Multi-bit Watermarking for AI-generated Text](https://www.usenix.org/conference/usenixsecurity25/presentation/qu-watermarking) | Reports 97.6% message match for 20 bits in 200 tokens in its comparison: 0.1 payload bits/token. Robustness can consume substantial cover length. |
| 2024 preprint; ICML 2025 | [Robust Multi-bit Text Watermark with LLM-based Paraphrasers](https://arxiv.org/abs/2412.03123) | Rewrites existing prose using two trained paraphrasers, then classifies sentence-level bit evidence. The closest direct precedent for watermarking one text with another. |
| STOC 2025 | [Ideal Pseudorandom Codes](https://eprint.iacr.org/2024/1840) | Strengthens adaptive robustness and develops linear-rate message constructions. Parameters and decoding costs need a concrete implementation. |
| 2025 preprint; STOC 2026 | [Improved Pseudorandom Codes from Permuted Puzzles](https://eprint.iacr.org/2025/2222) | Addresses prior quasipolynomial distinguishing attacks and constant-alphabet edit robustness under a new conjecture. Early PRCs are not a finished primitive. |
| January 2026; reviewed May v3 | [MirrorMark](https://arxiv.org/abs/2601.22246) | Maps symbols through mirrored pseudorandom sampling values or ranks. A scheduler balances payload positions and localizes edit effects. |
| February 2026; reviewed May v2 | [WorldCup Sampling for Multi-bit LLM Watermarking](https://arxiv.org/abs/2602.01752) | Hierarchical sampling as communication, with entropy-aware modulation and confidence-aware recovery. Relevant to uneven token reliability. |
| February 2026; reviewed May v2 | [ArcMark: Distortion-Free Multi-Byte LLM Watermark via Optimal Transport](https://arxiv.org/abs/2602.07235) | Random linear coding, optimal transport, and shared randomness. The reviewed decoder scores all candidate messages, so arbitrary ciphertext requires further coding work. |
| April 2026 preprint | [Undetectable Conversations Between AI Agents via Pseudorandom Noise-Resilient Key Exchange](https://arxiv.org/abs/2604.04757) | Theoretical bridge from watermarks to explicit covert payloads and near-entropy rates with an interaction-unique key. Private-context and key-exchange results extend beyond our shared-model codec. |
| May 2026; reviewed September v2 | [Covert Multi-bit LLM Watermarking: An Information Theory and Coding Approach](https://arxiv.org/abs/2605.16709) | Latest version studies non-autoregressive models, non-causal access within blocks, and polar coding. Not a capacity theorem for our causal Llama sampler. |
| ACL 2026 | [You Can Have a Second Chance](https://aclanthology.org/2026.acl-long.1297/) | Unbiased multi-bit watermarking for diffusion language models through stable contexts and remasking. An adjacent model-family branch. |
| September 2026 preprint | [CertMark](https://arxiv.org/abs/2609.33332) | Message-conditioned Gumbel-max randomness and decoding with an abstention certificate. Candidate enumeration occurs within chunks; inspect payload size, cost, and assumptions. |
| October 2026 preprint | [SimpleMark](https://arxiv.org/abs/2610.05712) | Explicit divergence constraints for each realized key and message, distinguished from average-key preservation. Its zero-capacity statement concerns the stronger exact conditional constraint. |

The existing [SparSamp](../2025-sparsamp/relevance.md),
[ANStega](../2026-anstega/relevance.md), and
[RRC](../2026-rrc/relevance.md) remain direct high-rate baselines for our model.
This bibliography expands the objectives to noisy recovery and message-carrying
watermarks; it does not displace those comparisons.

## What video recompression survival demonstrates

Video Seal estimates bits from individual frames, averages the soft predictions,
then thresholds the result. Its encoder and extractor train with transformations
between them, including codecs. See [Sections 2.2.3 and 2.3](https://arxiv.org/html/2412.09492v1).

The default 96-bit message is 12 bytes. The paper evaluates five-second clips
at their original resolution. A small message supported by many observations
is a robust channel, not evidence that a large secret was compressed into a tiny
signal. Video compression reduces the carrier's storage cost; watermark decoding
recovers only the embedded payload.

Source compression reduces the message's byte count. Encryption conceals its
meaning and adds authentication overhead. Error correction adds redundancy so
the receiver can repair damage. Repair capacity normally increases the space
needed per useful payload bit.

Detecting correlation with a known signature is easier than recovering an
unknown arbitrary message. High detection AUC or high average bit accuracy does
not establish an authenticated ciphertext round trip. For illustration,
independent 1% bit errors give only `0.99^256 ≈ 7.6%` probability of a completely
correct 256-bit block before correction. Real errors can be correlated; this
calculation is not an estimate for any cited method.

## Mapping video methods to text

These are proposed transfers to investigate, not implemented repository features.

| Video technique | Proposed text analogue | Condition to test |
| --- | --- | --- |
| Repeat or propagate evidence through frames | Spread a codeword across independently recoverable sentences or short blocks | Repetition reduces useful bits per token. |
| Average soft estimates before deciding | Accumulate token or sentence log-likelihood evidence for a soft decoder | Evidence can be correlated or miscalibrated. |
| Recover from crops and dropped frames | Treat missing sentences as erasures; add local indexing and resynchronization | Lost boundaries and insertions must not shift the whole payload. |
| Train through codecs and geometric changes | Train or evaluate through specified edits, paraphrasers, and formatting changes | One paraphraser's results do not generalize automatically. |
| Embed in a stable latent representation | Encode in sentence representations or with a trained paraphraser | Semantic similarity does not guarantee preservation of the encoded partition. |
| Preserve noise statistics while choosing realizations | Couple payloads to inverse-CDF, Gumbel, or mirrored sampling | Test key reuse, repeated contexts, truncation, and finite precision. |

A word replacement changes both the current symbol and the model's later
conditional probabilities. With a sequential arithmetic coder, adding an
ordinary error-correcting code around the ciphertext may therefore fail: one
edit can corrupt all subsequent decoded bits. Local recovery or an
insertion/deletion-aware design must precede assumptions about small,
independent error rates.

Sentence-level methods can preserve signal through mild paraphrasing. They
cannot preserve an unrelated payload through every rewrite that preserves the
visible meaning: a rewrite can collapse equivalent phrasings to one canonical
sentence, removing the choices that carried the secret. The
[paraphraser paper's Section 4.3](https://arxiv.org/html/2412.03123v2) explicitly
discusses this limit. A robustness target must name the allowed edits or their
distribution.

## Sampling values and capacity

An inverse-CDF sampler draws a uniform value and selects the vocabulary interval
containing it. Steganography couples the message to that choice. Gumbel-based
methods attach random values to candidates and select the winning score;
message-conditioned randomness creates a recoverable correlation. In both
cases, the receiver observes the selected token, not every floating-point digit
used inside the sampler.

For a fixed distribution and an unmodified channel, the average information in
the emitted choices bounds the recoverable payload. Under editing, the
information that survives the specified channel is what matters. Increasing
internal PRNG precision cannot itself increase what the visible tokens
communicate. The coupling and watermark capacity papers formalize different
versions of these limits under different assumptions.

Three security claims need separate treatment:

1. A token has the original distribution after averaging over randomness or keys.
2. A collection of outputs under a reused secret key is computationally
   indistinguishable from the reference generator.
3. The output matches actual correspondence, including length, topic, and sender
   behavior.

The first does not establish the second; neither establishes the third.
Gaussian Shading's cross-image correlations and later PRC designs make the
distinction concrete. SimpleMark's fixed-key/message constraint also explains
apparently conflicting distortion-free capacity claims. Its
conditional-memoryless analysis does not refute cryptographic concealment or
the coupling approach.

The image PRC paper distinguishes its proven zero-bit construction from the
heuristic undetectability argument for its long-message extension. Its
512/2,500-bit recovery results are empirical evidence within tested settings,
rather than a universal hidden-message recovery guarantee.

## Proposed next comparisons

Keep the [size-frontier experiment](../../experiments/004-size-frontier/README.md)
as the exact-transport branch. The previous
[size audit](../2026-10-22-size-plausibility/README.md) found that our arithmetic
coder already uses most selected entropy. Watermarking gives new recovery
designs; it does not establish a large reduction in those covers.

A separate robustness experiment should compare:

| Candidate | Research question |
| --- | --- |
| Current arithmetic codec, with ordinary unmodified sampling as a cover control | Establish transmitted size and how quickly isolated edits destroy recovery. |
| A message-carrying sampler based on MirrorMark or CertMark | Can locally reproducible evidence avoid dependence on exact replay throughout a message? |
| A PRC or another specified synchronization and coding design | Can substitutions and erasures be repaired at a practical full transmission size? |
| A sentence paraphraser channel | Can we preserve an existing public text's meaning while carrying an unrelated payload through mild edits? |

The proposed pipeline is:

```text
secret UTF-8 bytes
  -> optional lossless source compression
  -> authenticated encryption and framing
  -> channel coding and synchronization
  -> message-conditioned token sampling or sentence rewriting
  -> visible carrier text
  -> specified text transformations
  -> local evidence extraction and channel decoding
  -> authentication and exact recovery of the secret bytes
```

Measure useful recovered bytes per full transmitted byte and per token,
complete authenticated recovery probability, decoding time, and meaning changes.
Count nonces, tags, openings, redundancy, seeds, and correction traffic.
Evaluate formatting normalization, isolated edits, sentence deletion, and mild
paraphrasing separately. For rewritten covers, also measure preservation of
names, numbers, factual claims, and tone.

For concealment, use repeated messages and contexts under the same key as well
as fresh ones. Compare against the identical generator and the intended
correspondence population. Detection by the keyed receiver and detection by an
observer who lacks the key are different tests.

## Reading order and search record

Read the [SoK](https://arxiv.org/abs/2411.18479) for definitions, then
[Pseudorandom Error-Correcting Codes](https://arxiv.org/abs/2402.09370) and the
[image PRC paper](https://arxiv.org/abs/2410.07369) for the bridge between robust
watermarking and steganography. Follow with Video Seal's extraction method,
the text paraphraser paper, and the 2026 samplers above. Inspect ArcMark's
all-candidates decoder and CertMark's chunk size before choosing an implementation.

The search followed three histories: sampling steganography, message-carrying
generative watermarks, and recovery under image/video/text transformations.
It used primary papers, proceedings, author project pages, and the existing
archive. Discovery queries included `survey generative AI watermarking multi bit
arbitrary messages`, `pseudorandom error-correcting codes steganography`,
`multi-bit watermarking language models 2026`, `VideoSeal video compression
watermarking`, and `text watermarking paraphrase multi-bit`.

This is a targeted longitudinal review, not an exhaustive systematic review or
a meta-analysis of pooled results. Full-text sections were inspected for the
main surveys, image PRC, Video Seal, paraphraser, ArcMark, CertMark, and SimpleMark
claims; broader leads include abstract or proceedings-summary reviews. The
[source catalogue](sources.json) records that distinction and reviewed versions.
New source PDFs were not downloaded in this pass; older archived papers retain
their existing files and provenance.


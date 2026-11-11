# Prior Art

Studies on linguistic steganography, distribution control, source compression,
and reliable message recovery, with related work on message-carrying watermarks.

## Foundations

### [An Information-Theoretic Model for Steganography](https://cachin.com/cc/papers/stego.pdf)

1998; expanded paper, 2004. Defines steganographic security through the statistical
difference between ordinary cover objects and objects carrying hidden messages.
The analysis relates hypothesis testing and relative entropy to an observer's
ability to distinguish the two distributions.

### [Provably Secure Steganography](https://eprint.iacr.org/2002/137)

CRYPTO 2002. Develops a computational framework for steganographic security and
constructions based on sampling a communication channel. Security is expressed
through the difficulty of distinguishing hidden communication from ordinary
channel output.

## Generative linguistic steganography and coding

### [Neural Linguistic Steganography](https://aclanthology.org/D19-1115/)

EMNLP-IJCNLP 2019. Uses a neural language model's next-token probabilities with
arithmetic coding to map secret bits into generated text and recover them. The
paper examines embedding rate and resemblance to the language model's output.

### [Near-imperceptible Neural Linguistic Steganography via Self-Adjusting Arithmetic Coding](https://aclanthology.org/2020.emnlp-main.22/)

EMNLP 2020. Introduces self-adjusting arithmetic coding for embedding information
in language-model generation. It studies how coding adjustments affect embedding
efficiency, distributional similarity, and human judgments of generated text.

### [Provably Secure Generative Linguistic Steganography](https://arxiv.org/abs/2106.02011)

Findings of ACL-IJCNLP 2021. Introduces Adaptive Dynamic Grouping (ADG), which
recursively groups candidate tokens according to their probabilities and uses
message bits to choose groups. The paper analyzes the resulting distribution and
evaluates generated text on several corpora.

### [Meteor: Cryptographically Secure Steganography for Realistic Distributions](https://www.cs.umd.edu/users/kaptchuk/publications/ccs21_meteor.pdf)

ACM CCS 2021. Develops cryptographic steganographic sampling for generative
distributions whose entropy varies across positions. It combines shared
cryptographic randomness with message-driven sampling and includes text-generation
and implementation experiments.

### [Discop: Provably Secure Steganography in Practice Based on Distribution Copies](https://ding.ac.cn/uploads/Discop_sp23_paper.pdf)

IEEE Symposium on Security and Privacy 2023. Embeds messages by selecting among
shifted copies of a probability distribution. The construction uses shared
randomness and recursive embedding to preserve the sampling distribution under
its stated assumptions.

### [Perfectly Secure Steganography Using Minimum Entropy Coupling](https://arxiv.org/abs/2210.14889)

ICLR 2023. Formulates distribution-preserving steganography as a coupling between
message and cover distributions. It connects maximizing the information conveyed
about a message with minimizing the joint entropy of that coupling.

### [Computing Low-Entropy Couplings for Large-Support Distributions](https://proceedings.mlr.press/v244/sokota24a.html)

UAI 2024. Develops algorithms for constructing low-entropy couplings when
distributions have large support or autoregressive structure. Its applications
include steganography, using the ARIMEC algorithm.

### [SparSamp: Efficient Provably Secure Steganography Based on Sparse Sampling](https://www.usenix.org/conference/usenixsecurity25/presentation/wang-yaofei)

USENIX Security 2025. Uses sparse sampling to embed messages while preserving the
cover distribution under the paper's security model. It studies embedding
capacity and the computational cost of steganographic sampling.

### [Shimmer: a Provably Secure Steganography Based on Entropy Collecting Mechanism](https://www.usenix.org/conference/usenixsecurity25/presentation/bai-minhao)

USENIX Security 2025. Collects residual entropy from one embedding step for use
in later steps. The method also addresses interval splitting as a source of
embedding-rate loss.

### [Breaking the Generative Steganography Trilemma: ANStega for Optimal Capacity, Efficiency, and Security](https://www.ndss-symposium.org/wp-content/uploads/2026-f605-paper.pdf)

NDSS 2026. Combines streaming asymmetric numeral system (ANS) coding with
cryptographic masking for generative steganography. The paper studies capacity,
distribution preservation, and coding efficiency; decoding also uses a final ANS
state.

### [Efficient Provably Secure Linguistic Steganography via Range Coding](https://aclanthology.org/2026.acl-long.39/)

ACL 2026. Proposes RRC, a range-coding construction for distribution-preserving
linguistic steganography. It evaluates embedding rate, entropy utilization, and
runtime, with implementation details covering numerical precision and termination.

### [Provably Secure Steganography Based on List Decoding](https://arxiv.org/abs/2604.21394v3)

2026 arXiv preprint, version 3. Maintains a list of candidate messages
across generated tokens and uses a suffix to resolve the remaining ambiguity.
The paper studies achievable embedding rates and decoding costs.

### [Provable Secure Steganography Based on Adaptive Dynamic Sampling](https://www.usenix.org/conference/usenixsecurity26/presentation/pang-kaiyi)

USENIX Security 2026. Studies steganography through a sampling interface that
accepts random seeds without exposing the complete next-token probability
distribution. Its construction relies on reproducible samples for supplied seeds.

### [From Symmetry toward Weak Asymmetry: Secure Steganography under the Receiver's Partial Channel Knowledge](https://www.usenix.org/conference/usenixsecurity26/presentation/liao)

USENIX Security 2026. Investigates decoding when the receiver has partial channel
information, such as token rankings, rather than exactly matching probabilities.
It develops constructions and experiments for this asymmetric-information setting.

### [HiTMS: A High-Throughput Multi-Stream Linguistic Steganography Framework](https://arxiv.org/abs/2607.23597v2)

2026 arXiv preprint, version 2. Introduces framing and scheduling for
multiple steganographic generation streams. It studies batching and parallel
execution to increase transmission throughput.

## Distribution control and adjustable embedding rates

### [Linguistic Steganography via Self-Adjusting Asymmetric Number System](https://aclanthology.org/2026.cl-1.4/)

Computational Linguistics, volume 52, issue 1, 2026. Proposes SA-ANS, combining
ANS-based probabilistic coding with adaptive candidate selection. The framework
supports user-specified embedding rates and evaluates linguistic quality,
statistical similarity, and extraction performance.

### [OD-Stega: LLM-Based Relatively Secure Steganography via Optimized Distributions](https://aclanthology.org/2026.eacl-long.36/)

EACL 2026. Maximizes the entropy of a replacement next-token distribution subject
to a KL-divergence or total-variation constraint relative to the model's original
distribution. The paper also studies adaptive distortion budgets and vocabulary
truncation.

### [Constant Composition Distribution Matching](https://arxiv.org/abs/1503.05133)

2015 arXiv preprint. Presents invertible mappings from uniform input bits to
fixed-length symbol sequences with a prescribed composition. It analyzes how
the achievable rate and distributional divergence behave as block length grows.

### [Bandwidth Efficient and Rate-Matched Low-Density Parity-Check Coded Modulation](https://arxiv.org/abs/1502.02733v2)

2015 arXiv preprint, version 2. Combines a distribution matcher with
systematic error-correcting coding for probabilistic signal shaping. Transmission
rate is adjusted through the input distribution and transmission power in the
paper's modulation setting.

## Tokenization and synchronization

### [Provably Secure Disambiguating Neural Linguistic Steganography](https://arxiv.org/abs/2403.17524v2)

IEEE Transactions on Dependable and Secure Computing, online 2024; author
preprint version 2. Introduces SyncPool, which groups token pieces with
ambiguous prefixes and uses synchronized cryptographic randomness within groups.
The method addresses recovery when different token sequences produce the same
visible text.

### [Addressing Tokenization Inconsistency in Steganography and Watermarking Based on Large Language Models](https://aclanthology.org/2025.emnlp-main.361/)

EMNLP 2025. Introduces stepwise verification of candidate tokens to detect
inconsistencies between generation tokenization and the receiver's retokenization.
It filters problematic candidates and evaluates extraction reliability and cost.

### [A High-Capacity and Secure Disambiguation Algorithm for Neural Linguistic Steganography](https://arxiv.org/abs/2510.02332)

2025 arXiv preprint. Proposes look-ahead Sync, which examines future token paths
to distinguish alternatives that share visible prefixes. Synchronized sampling is
reserved for paths that remain indistinguishable.

### [ReTokSync: Self-Synchronizing Tokenization Disambiguation for Generative Linguistic Steganography](https://arxiv.org/abs/2604.25486)

2026 arXiv preprint. Resets generation state to the receiver's retokenized view
when tokenization ambiguity occurs, limiting subsequent desynchronization. Its
evaluation includes bit recovery and an additional correction-message protocol.

## Source compression

### [LLMZip: Lossless Text Compression using Large Language Models](https://arxiv.org/abs/2306.04050v2)

2023 arXiv preprint, version 2. Uses a language model's next-token
predictions with lossless coding to compress text. The paper also uses prediction
quality to estimate an upper bound on the entropy of English under its setup.

### [StegoZip: Enhancing Linguistic Steganography Payload in Practice with Large Language Models](https://proceedings.neurips.cc/paper_files/paper/2025/hash/6c8e215afa321d5d0b295dc1882820df-Abstract-Conference.html)

NeurIPS 2025. Processes secret text before embedding using semantic redundancy
pruning and index-based compression. Restoration uses a trained model and explicit
correction information to reconstruct the source message.

### [ts_sms](https://bellard.org/ts_sms/) and [ts_zip](https://bellard.org/ts_zip/)

Author-maintained compression tools; ts_sms released December 2024.
ts_sms targets short messages using language-model compression and a padding
scheme that avoids a separate message-length field. ts_zip provides language-model
text compression and documents reproducible inference settings.

## Robustness and error correction

### [STEAD: Robust Provably Secure Linguistic Steganography with Diffusion Language Model](https://papers.nips.cc/paper_files/paper/2025/hash/3d03800841fa1bb2f43ef1750aafcce4-Abstract-Conference.html)

NeurIPS 2025. Combines diffusion language models and error correction for
linguistic steganography that tolerates damaged cover text. The evaluation
includes token insertions, deletions, and substitutions.

### [TE-CSA: trajectory entropy-aware cross-step aggregation for improving embedding capacity of distribution-preserving linguistic steganography](https://link.springer.com/article/10.1186/s42400-026-00668-2)

Cybersecurity, October 2026. Aggregates embedding opportunities across the
denoising trajectory of a diffusion language model. The construction uses a
distribution-preserving embedding mechanism and studies capacity and robustness.

### [Pseudorandom Error-Correcting Codes](https://arxiv.org/abs/2402.09370v2)

CRYPTO 2024; preprint version 2. Constructs codes whose codewords appear
pseudorandom to an observer while a key enables recovery after specified errors.
Applications include robust language-model watermarking and stateless steganography
under stated cryptographic assumptions.

### [Edit Distance Robust Watermarks via Indexing Pseudorandom Codes](https://arxiv.org/abs/2406.02633v2)

NeurIPS 2024; author version 2. Develops indexing pseudorandom codes
and watermark constructions that tolerate adversarial insertions, deletions, and
substitutions. The guarantees include assumptions on alphabet size and
cryptographic hardness.

## Message-carrying text watermarks

### [Multi-Bit Distortion-Free Watermarking for Large Language Models](https://arxiv.org/abs/2402.16578v1)

2024 arXiv preprint. Extends keyed sampling watermarks to carry recoverable
metadata through Distribution Interval Shift Coding. It also develops a decoder
for extracting the embedded bits.

### [Distributional Information Embedding: A Framework for Multi-bit Watermarking](https://arxiv.org/abs/2501.16558v2)

2025 arXiv preprint, version 2. Formulates message embedding by
controlling the distribution of generated text. It analyzes information rate,
distortion, and detection in asymptotic and finite-token settings.

### [StealthInk: A Multi-bit and Stealthy Watermark for Large Language Models](https://arxiv.org/abs/2506.05502v1)

ICML 2025. Embeds provenance metadata through distribution-preserving sampling
under its watermarking model. Extraction does not require the generating model's
API or the original prompt.

### [Robust Multi-bit Text Watermark with LLM-based Paraphrasers](https://arxiv.org/abs/2412.03123v2)

ICML 2025. Uses two fine-tuned paraphrasers to encode bits at sentence level and
a trained classifier to decode them. The paper evaluates recovery under word
substitution and sentence paraphrasing.

### [WorldCup Sampling for Multi-bit LLM Watermarking](https://arxiv.org/abs/2602.01752v2)

2026 arXiv preprint, version 2. Models hierarchical token sampling as a
communication channel. It combines entropy-aware message modulation with decoding
that accounts for the reliability of individual tokens.

### [ArcMark: Distortion-Free Multi-Byte LLM Watermark via Optimal Transport](https://arxiv.org/abs/2602.07235v2)

2026 arXiv preprint, version 2. Uses coding, optimal transport, and shared
randomness to embed multi-byte messages in generated text. It develops a
channel-capacity formulation and evaluates message reconstruction, including
after text alterations.

## Message-carrying image and video watermarks

### [An Undetectable Watermark for Generative Image Models](https://arxiv.org/abs/2410.07369v4)

ICLR 2025; author version 4. Uses pseudorandom codes to select diffusion
latents that carry a watermark. The work studies cryptographic undetectability,
robustness, and the recovery of embedded messages from generated images.

### [Video Seal: Open and Efficient Video Watermarking](https://arxiv.org/abs/2412.09492v1)

2024 arXiv preprint, version 1. Trains a video embedder and extractor
through transformations including video compression. The extractor combines soft
bit evidence across frames to recover a message.

## Survey

### [A Comprehensive Survey on Linguistic Steganography: Methods, Countermeasures, Evaluation, and Challenges](https://arxiv.org/abs/2608.29077v1)

2026 arXiv survey; authors report EMNLP 2026 acceptance. Organizes
linguistic steganographic methods, steganalysis techniques, evaluation measures,
and practical challenges. Its bibliography includes generation-based coding,
tokenization, and robustness research.

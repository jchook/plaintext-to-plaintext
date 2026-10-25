# Research leads for denser and recoverable cover text

Collected October 23, 2026. These are potential research directions for the
plaintext-to-plaintext system, with emphasis on ideas from constrained storage,
communications, compression, and steganography. They extend the existing
[watermarking review](../2026-10-22-watermarking/README.md) and preserve the
follow-up findings from the Video Seal review.

The most promising connections are short-message compression for reducing fixed
costs, distribution shaping for increasing useful bits per visible byte, and DNA
storage codecs for recovering through edits with less redundancy than repetition.
The transfers below are hypotheses, not demonstrated improvements to this codec.
The current [size and quality priorities](../../EXPERIMENTS.md) remain the baseline.

## What an improvement must achieve

Compare complete transmitted UTF-8 bytes at a declared payload size, prose-quality
threshold, and authenticated recovery rate through specified transformations.
Count the public opening, framing, termination, block identifiers, correction
data, and any additional messages. Report packed-source bits and encrypted-frame
bits separately; original input length is not a measure of independent information.

Robustness adds redundancy. A useful code can reduce that cost relative to naive
repetition, but extra correction bits do not themselves increase net payload
density. A scheme can also carry more bits per token while using longer token
pieces, producing no gain per visible byte.

The [saved-cover density audit](../2026-10-22-encoding-density-audit/README.md)
identifies framing and the public opening as substantial costs. The
[size audit](../2026-10-22-size-plausibility/README.md) also finds that the current
arithmetic coder uses most of its selected distribution's entropy. These findings
favor reducing overhead and improving available choices before assuming a new
entropy coder will yield a large gain.

## Projects and possible transfers

### Short-message compression with ts_sms

Fabrice Bellard's [ts_sms](https://bellard.org/ts_sms/) has a December 2024 release
and uses language-model compression with arithmetic-compatible padding that avoids
an explicit message-length field. Its companion
[ts_zip](https://bellard.org/ts_zip/) documents reproducible model evaluation
across hardware configurations. The 2023
[LLMZip paper](https://arxiv.org/abs/2306.04050) is another reference for predictive
lossless text compression.

Potential transfer: compare termination and source-framing designs on our short
payloads. We already compress before encryption; the question is how many total
bytes a complete source representation requires, including validation and decoder
dependencies. A smaller shared model specialized for compression could also be
compared with our current source model.

Inspect the padding algorithm and licensing before choosing an implementation.
Avoiding one length field does not remove the nonce or authentication tag. Keep
restored-source validation: authenticated compressed bytes can still decompress
incorrectly if model probabilities differ between runtimes. Stronger compression
can also increase computation and compatibility requirements.

### Constrained encoding and repair with DNA-Aeon and HEDGES

[DNA-Aeon](https://www.nature.com/articles/s41467-023-36297-3) (2023) combines
arithmetic coding into allowed DNA sequences, periodic checks, a stack-based
decoder that searches possible error paths, and an outer Raptor fountain code for
missing fragments. Its [implementation](https://github.com/MW55/DNA-Aeon)
describes the codebooks and concatenation constraints.
[HEDGES](https://finkelsteinlab.org/assets/md/2020-07-16-HEDGES/) (2020) uses
hash-dependent encoding and bounded hypothesis search to correct insertions,
deletions, and substitutions. It combines inner synchronization repair with an
outer Reed-Solomon code. [HEDGES code](https://github.com/whpress/hedges) is public.

Potential transfer: use efficient local text encoding, a bounded decoder that
repairs isolated damage, and an outer code that recovers missing or rejected
blocks. Compare that combination with simple repetition at matched recovery
rates. Deliberate redundancy and a scoring rule let a decoder reject wrong paths;
hashing history alone does not supply error correction.

DNA constraints have simpler structure than language-model conditionals. A text
implementation must reconstruct plausible original token histories and limit
model calls, memory, and search time. HEDGES also identifies termination overhead
that makes very short strands inefficient. Small text blocks may face a similar
penalty, so block size is an experimental variable.

### Distribution matching and probabilistic shaping

[Constant Composition Distribution Matching](https://arxiv.org/abs/1503.05133)
(2015 preprint) reversibly maps uniform input bits to sequences with a desired
nonuniform composition. The related
[probabilistic shaping and coding work](https://arxiv.org/abs/1502.02733) (2015)
combines a distribution matcher with error correction and adapts the rate through
the input distribution.

Potential transfer: optimize the sampling distribution and correction overhead
together. For our channel, evaluate useful recoverable bits per visible byte under
a declared distribution-change budget and prose-quality threshold. Token length,
termination probability, and local reliability could enter the objective instead
of maximizing next-token entropy alone. The existing
[OD-Stega note](../2026-od-stega/relevance.md) is the more direct text reference
for controlling divergence.

Fixed-composition blocks do not reproduce an autoregressive language model's
joint distribution. Short blocks also incur rate loss. Use these projects as
design references; their communication-channel guarantees do not establish text
concealment or edit robustness.

### Choosing low-cost rewrites with syndrome-trellis codes

The [syndrome-trellis code project](https://dde.binghamton.edu/download/syndrome/)
includes the 2010 and 2011 papers and a C++/MATLAB toolbox. Its embedding method
chooses among representations of a payload to minimize assigned additive
distortion costs.

Potential transfer: embed into an existing public draft using alternative sentence
or phrase realizations. Give alternatives costs for visible length, awkwardness,
changed facts, and sensitivity to the allowed edits. Choose a combination that
satisfies the payload constraints while minimizing those costs. Compare payload
at a fixed acceptable editing budget.

Language changes interact, so independent per-position costs are an approximation.
The receiver needs a reproducible mapping from observed text to symbols. The
original embedding method does not by itself make that mapping robust to edits,
and low distortion does not prove statistical concealment.

### Entropy use with minimum entropy coupling and Shimmer

[Minimum entropy coupling](https://arxiv.org/abs/2210.14889) (ICLR 2023) connects
distribution-preserving steganography with maximum information throughput under
its model. The [existing local note](../2023-minimum-entropy-coupling/relevance.md)
and [ARIMEC](../2024-arimec/relevance.md) provide starting points.
[Shimmer](https://www.usenix.org/conference/usenixsecurity25/presentation/bai-minhao)
(USENIX Security 2025) collects residual entropy across embedding steps and
addresses interval-splitting losses.

Potential transfer: add a matched density comparison alongside
[SparSamp](../2025-sparsamp/relevance.md), [RRC](../2026-rrc/relevance.md), and
[ANStega](../2026-anstega/relevance.md). Hold the model, prompt, candidate support,
and payload constant. Measure short-message termination costs, auxiliary state,
visible-text recovery, and speed as well as bits per token.

Our current entropy utilization leaves limited demonstrated headroom within the
selected support. A larger gain would need an identified loss, different usable
choices, or lower overhead. Neither coupling theory nor Shimmer creates extra
entropy in an unchanged channel.

### Synchronization strings and pseudorandom error-correcting codes

[Synchronization strings](https://par.nsf.gov/servlets/purl/10121528) (2017)
provide indexing constructions that help convert insertion and deletion errors
into errors conventional codes can handle.
[Pseudorandom Error-Correcting Codes](https://arxiv.org/abs/2402.09370) (2024)
combine keyed recovery with computationally pseudorandom codewords under stated
assumptions, including a steganography application.

Potential transfer: protect block identity separately from block contents, then
evaluate coding constructions whose redundancy does not expose an unintended
statistical pattern through the chosen embedding channel. Ordinary error
correction after encryption produces structured codewords; whether that structure
is observable depends on the complete sampler and security model.

Indexing occupies capacity, and theoretical rates do not settle small-message
costs. A practical design needs concrete parameters, decoding budgets, and an
authenticated arbitrary-message test. The
[existing watermarking review](../2026-10-22-watermarking/README.md) records later
PRC developments and assumption changes; consult those before selecting a primitive.

## Additional lessons from Video Seal

The [December 2024 paper](https://arxiv.org/html/2412.09492v1) adds several useful
constraints to the ideas above:

- Sections 2.2.3 and 5.3 extract soft evidence locally and combine it before deciding
  bits. Table 7 finds little benefit from elaborate confidence weighting over
  simple averaging. Start with a simple aggregator once a local text extractor exists.
- Section 5.2 improves extraction while holding the embedder fixed. Our possible
  analogue is bounded reconstruction of damaged saved covers, with acceptance
  only after authentication and the applicable original-cover checks succeed.
- Sections 2.3.3 and 5.1 support designing for the actual transformation channel.
  Test formatting changes, substitutions, deletions, and named paraphrasers separately.
- Section 3.1 and Appendix A.1 compare payloads using bit accuracy and a modeled
  detection score. Those measures do not establish complete authenticated recovery
  or an observer's empirical false-positive rate on our text.

Our [candidate ordering](../../poc/p2p.py) depends on the complete token history.
Independent blocks would need to reset the arithmetic interval, model history,
and history-derived keyed ordering. A sentence delimiter alone cannot resynchronize
the codec. The [opening protocol](../../poc/opening.py) also binds the exact public
opening into configuration and key derivation and checks the exact completion
suffix. Normalizing either region requires an explicit compatible protocol design.

## Candidate experiments

These are leads to choose from as the system advances, not a replacement for the
current experiment plan. Declare the payloads, damage distribution, quality rubric,
and required recovery rate before ranking results.

| Priority | Comparison | Decision it would support |
| --- | --- | --- |
| First density check | Current source format versus a short-message termination design informed by ts_sms | Is there a meaningful total-byte saving after validation and framing? |
| First distribution check | Current temperature policy versus a byte-cost-aware policy under a declared divergence budget | Can density improve while meeting the same quality threshold? |
| First recovery check | Current decoder versus bounded reconstruction on the same saved covers | Does extra receiver computation repair isolated edits without extra cover bytes? |
| Larger robustness prototype | Local blocks with repair and outer coding versus repetition | What block size and redundancy minimize full size at the required recovery rate? |
| Alternative carrier | Costed sentence rewrites versus generated continuation | Can useful payload fit into an existing draft with acceptable meaning and style changes? |
| Matched coder benchmark | Current arithmetic codec versus a selected modern sampler | Is there a measured loss worth a coder replacement? |

For recovery tests, vary damage location across the opening, payload, and suffix.
Separate newline conversion, quote wrapping, punctuation changes, word replacement,
sentence deletion, and paraphrasing. Retain all failures and cap repair search.
Compare final recovered bytes with the original and require authentication before
releasing plaintext.

For density tests, keep exact unmodified recovery as a prerequisite. Assess prose
quality separately from observer detectability, using both ordinary output from
the agreed generator and the intended correspondence population as controls.

## Source scope

This collection links primary papers and author project documentation consulted
for the discussion. The Video Seal follow-up included a sub-agent review of the
full paper and repository. The other leads have different review depths: HEDGES
full-text passages, project documentation for DNA-Aeon and Bellard's tools, and
paper abstracts or proceedings summaries for several coding constructions.
Published experiments have not been reproduced here. New PDFs, source checkouts,
and benchmark results are not part of this collection; the original archive's
counts and provenance records remain unchanged.

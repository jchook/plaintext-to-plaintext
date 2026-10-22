# Smaller stegotext: capacity, plausibility, and detection

Reviewed 2026-10-22. This follow-up combines primary-source reading with a
retrospective audit of experiment 003. It contains no new generated covers or
detection results. The [source record](sources.json) distinguishes downloaded
papers, existing archive material, and online abstract review.

The next useful target is **minimum complete cover size at an acceptable level
of plausibility**, with detectability measured separately. Our implementation
has avoidable costs, but its arithmetic coder already uses most of the entropy
in its selected token distribution. A rewrite of that component alone has no
demonstrated large size benefit.

## Define what we are optimizing

| Measure | Question | How to measure it |
| --- | --- | --- |
| Complete size | How much must the sender transmit? | UTF-8 bytes, words, tokens, extra state, and any additional messages. Include the public opening and completion suffix. |
| Plausibility | Would this sender reasonably send this message here? | Blind assessment of fluency, purpose, sender/recipient continuity, unsupported claims, and appropriate length. |
| Detectability | Can an observer distinguish it from ordinary traffic? | Held-out detector performance against declared reference traffic, plus distribution diagnostics. |
| Recovery | Does the recipient get the original? | Authenticated byte equality through the actual visible-text channel. |

Length belongs in plausibility. A polished ten-paragraph conference follow-up
may fit the situation less well than three ordinary sentences. Adding prose
does not itself improve quality. Likewise, lowering perplexity is not proof of
lower detectability: repeatedly choosing only the most likely words changes
the distribution too.

The distinction has precedent. [Lin et al., NAACL 2024](https://aclanthology.org/2024.naacl-long.289/),
especially sections 2 and 4.4, discuss disagreement between perceptual and
statistical imperceptibility. Their model-to-human distribution gap is especially
relevant to our emails. The specific question of whether our current openings
make correspondence plausible remains an empirical question.

We should report two detection comparisons:

1. Against ordinary samples from the same model, prompt, and declared sampling
   policy. This isolates changes introduced by embedding.
2. Against legitimate correspondence for the intended setting, including its
   length distribution. This asks whether the whole system fits its use.

Neither comparison substitutes for the other. Human judgments and statistical
detectors can disagree; report both rather than combining them into a claimed
probability of being safe. We have measured neither detection comparison yet.

## Where the bytes currently go

[audit.py](audit.py) checks the saved input/cover/recovered files and hashes for
all 32 pilot trials and reproduces [audit.json](audit.json). The table pools the
three opening fixtures at temperature 1.2, with two repetitions each, so each
column has six observations. These means describe this small pilot.

| Component | Short message | Paragraph |
| --- | ---: | ---: |
| Original private input | 16 B | 238 B |
| Losslessly packed source | 17 B | 49 B |
| Encrypted frame, including packed source | 47 B | 79 B |
| Public opening plus separator | 375 B | 375 B |
| Generated prose carrying the frame | 834.2 B | 1,415.8 B |
| Sentence-completion suffix | 88 B | 33.7 B |
| **Complete transmitted cover** | **1,297.2 B** | **1,824.5 B** |

The last three components sum to the complete cover. The encrypted frame is
encoded into the generated prose; it is not a separate visible addition.
The frame adds 30 bytes: a 12-byte nonce, a two-byte length, and a 16-byte
authentication tag. That overhead accounts for 64% of the short frame and 38%
of the paragraph frame. This is a fixed-cost problem for short secrets.

The paragraph is already compressed from 238 to 49 bytes. Source compression is
therefore an existing strength, although two payloads do not establish its
performance on arbitrary text. Source compression happens before encryption;
the encrypted bytes are not another useful compression target.

The carrying prose averages about five visible bytes per generated payload
token. At temperature 1.2, pooled frame rates are 2.24 bits/token for the short
message and 2.26 for the paragraph. Their token-count-weighted table entropies
are 2.25 and 2.36 bits/token. Sampling and finite-message effects matter; these
figures do not imply a strict per-file utilization bound.

Within the returned top-64 support, the additional printable/prefix-free
filter reduces the mean entropy by about 0.08–0.11 bits/token in these groups.
That points to a modest average opportunity within this support, not a known
multi-fold gain. Full-vocabulary entropy was not recorded. Omitted probability
mass alone does not tell us how much entropy we lost.

Increasing temperature from 1.0 to 1.2 already reduced mean full size from
1,707.7 to 1,297.2 bytes for the short message, and from 2,441 to 1,824.5 for the
paragraph. Those are descriptive reductions of 24% and 25%, respectively.
There is no detection result accompanying them, and each setting has different
generated histories.

## The limits and the papers that explain them

[Cachin's information-theoretic model](https://cachin.com/cc/papers/stego.pdf)
treats detection as distinguishing two distributions. The work began with the
1998 Information Hiding paper; our newly archived copy is the expanded March
2004 version. [Hopper, Langford, and von Ahn, CRYPTO 2002](https://www.iacr.org/archive/crypto2002/24420077/24420077.pdf)
give computational indistinguishability definitions. This problem has a much
longer history than the current generation of language models.

For a fixed generative channel, the conditional entropy of its choices limits
the average hidden bits obtainable while preserving that distribution. Choices
that are almost predetermined carry little information. A more varied channel
can carry more. The relevant bound depends on the model, context, channel,
shared information, and security requirement, not just the English language.

Our approximate size accounting is:

```text
complete cover bytes
    ≈ public opening bytes + separator bytes + ending bytes
      + 8 × encrypted frame bytes × visible bytes/token ÷ frame bits/token
```

This explains why bits/token alone is an incomplete objective. A different
tokenizer or sampling policy also changes visible bytes/token. The optimization
we need is recovered payload per complete transmitted byte.

| Primary source | What it contributes | Consequence for this project |
| --- | --- | --- |
| [Ziegler, Deng, and Rush, EMNLP 2019](https://aclanthology.org/D19-1115/) | Neural language models with arithmetic coding. | Our core construction has direct precedent. |
| [Meteor, CCS 2021](../2021-meteor/relevance.md) | Cryptographic analysis for realistic, uneven token distributions. | Round-trip correctness alone gives no distributional security guarantee. |
| [Minimum entropy coupling, ICLR 2023](https://arxiv.org/abs/2210.14889) | Characterizes distribution-preserving steganography through couplings and throughput through minimum entropy coupling. | A theoretical reference for preserving the cover distribution while using its available choices. |
| [Lin et al., NAACL 2024](https://aclanthology.org/2024.naacl-long.289/) | Separates perceptual and statistical evaluation and uses in-context examples. | Evaluate the generated continuation and the whole email against their intended setting. |
| [SparSamp, USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/wang-yaofei) | Efficient provably secure sampling. | A modern comparison for coding efficiency and security. |
| [StegoZip, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/6c8e215afa321d5d0b295dc1882820df-Abstract-Conference.html) | Compresses the secret before embedding; reports 2.5 times baseline payload. | Compare against our existing source coder, including restoration corrections and all decoding dependencies. |
| [OD-Stega, EACL 2026](https://aclanthology.org/2026.eacl-long.36/) | Maximizes next-token entropy under a KL or total-variation budget. | Direct research basis for a capacity slider with a declared distribution budget. |
| [RRC, ACL 2026](https://aclanthology.org/2026.acl-long.39/) | Range coding with reported near-full entropy use. | A matched coder comparison; its documented retokenization failures must be addressed. |
| [ANStega, NDSS 2026](https://www.ndss-symposium.org/wp-content/uploads/2026-f605-paper.pdf) | ANS-based embedding with reported near-entropy rates. | Another comparison, counting the decoder's required final state as part of transmission. |

These results were not reproduced here. Model sizes, prompts, tokenizers, and
protocol assumptions differ. For example, RRC's Llama-2-7B comparison reports
3.57 bits/token versus SparSamp's 3.38; this is a useful matched comparison,
not evidence that replacing our coder produces that rate on our model. See
the [earlier review](../summary.md) for runtime and tokenization caveats.

## A slider with a defensible meaning

Use **closer to ordinary generation** at one end and **shorter cover** at the
other. Treat plausibility as a measured constraint across the slider. Labeling
one endpoint "undetectable" or "high plausibility" would promise a result we
have not established.

OD-Stega supplies a specific starting point: maximize the next-token entropy
subject to `D_KL(Q || P) ≤ δ`, where `P` is the reference distribution and `Q`
is the distribution used to embed. Its KL solution is temperature scaling,
with temperature chosen to satisfy the budget. This supports adaptive control
instead of applying the same temperature to every position. It does not by
itself optimize bytes per complete email or prove human plausibility.

A per-token budget is also not a whole-message guarantee. Sequence KL sums
the expected conditional divergences. Variable length, public openings,
candidate exclusions, and our deterministic ending policy need accounting.
The control should record a cumulative distribution budget and total size;
its value is not a measured detection probability.

For intuition, suppose ordinary next-word probabilities are 90% for one choice
and 10% for another. Their entropy is about 0.47 bits. Treating them as equally
likely carries one bit per choice, but the originally rare word now appears
half the time. A single sentence can still look fine while repeated messages
reveal the changed frequencies. A simpler uniform/rank-based method may thus
produce shorter output by accepting a different distribution. Include it as a
baseline and measure that tradeoff.

There is no reason to pay a quality cost for every saved byte. Shorter public
openings or better lossless compression can improve size without deliberately
flattening token probabilities. First remove those costs, then measure the
remaining frontier between size, writing quality, and detectability.

## Highest-value next steps

1. Test short public openings while retaining the current arbitrary-opening
   interface. Replacing a mean 373-byte opening with a 60-byte opening would
   directly remove 313 visible bytes if the continuation were unchanged: 24%
   of the short cover or 17% of the paragraph cover. This is arithmetic, not a
   measured result; a shorter opening can also change the continuation.
2. Instrument the token distribution before changing the coder. Record entropy,
   expected visible bytes, candidate count, truncation/filter losses, table
   distortion, and low-entropy stretches. Compare a wider support and a safe
   text-decoding alternative under the same model and prompt. Preserve exact
   visible-text recovery, not merely recovery from token IDs.
3. Compare fixed temperature, adaptive divergence control, and a simple uniform
   rank baseline. Rank results by complete bytes after rejecting failures and
   measuring plausibility. Keep the framing, model, and prompt fixed within
   this comparison.
4. Inspect ending and framing overhead separately. The ending is about 34–88
   bytes in these groups, so it is a smaller average cost than carrying the
   frame. The 30-byte frame matters greatly for tiny inputs, but removing the
   authentication tag or assuming synchronized nonce state changes the
   requirements. Any alternate frame needs its own protocol/security review.

For scale, a hypothetical 79-byte frame at four bits/token and five visible
bytes/token needs about 790 carrying bytes. Adding a 375-byte opening and a
34-byte ending gives about 1,199 bytes. This illustrates the rate leverage;
it is neither a lower bound nor a prediction for a new sampler.

The [experiment 004 plan](../../experiments/004-size-frontier/README.md)
turns these questions into staged comparisons. Begin with the accounting and
short-opening controls, then test the distribution policy. Keep experiment
003 and its original prompts unchanged for replay.

## Reproduce this review's local accounting

From the repository root:

```sh
python3 research/2026-10-22-size-plausibility/audit.py --check
python3 experiments/verify.py
```

The audit validates saved bytes and recomputes aggregates. It does not replay
inference, reproduce the papers, or test detection. The two added PDFs and
their extracted text have hashes in [downloads.json](sources/downloads.json).
The previous 28-source archive and its original verification record remain
historical records of the October 18 review.

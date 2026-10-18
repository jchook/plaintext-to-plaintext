# Breaking the Generative Steganography Trilemma: ANStega for Optimal Capacity, Efficiency, and Security

NDSS 2026. Reviewed 2026-10-18.

Near-entropy streaming ANS with cryptographic masking and low coding overhead. Particularly relevant to our size target: reports 3.69 bits/token on Qwen2.5-3B and 4.67 on Phi-2 2.7B in its full-vocabulary experiments.

The decoder consumes the embedder's final ANS state. Transporting or reconstructing that state must be accounted for before treating this as a self-contained cover-text protocol. Numerical compatibility remains necessary.

[Original source](https://www.ndss-symposium.org/wp-content/uploads/2026-f605-paper.pdf)

[Paper PDF](paper.pdf) · [Searchable text](paper.txt)

[Download provenance and checksums](metadata.json). Reported results were not reproduced here.

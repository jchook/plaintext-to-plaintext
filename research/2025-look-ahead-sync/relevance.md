# A High-Capacity and Secure Disambiguation Algorithm for Neural Linguistic Steganography (Look-ahead Sync)

2025 arXiv preprint. Reviewed 2026-10-18.

Retains distinguishable future token paths instead of immediately discarding prefix-overlapping candidates. On Llama3-8B, IMDB, top-k 128 with Discop, reports 2.66 bits/token versus SyncPool's 0.95.

The same setting produces about 0.42 tokens per model call, or 2.38 calls per token. Capacity gains can increase latency. No author implementation was established during the review; theoretical assumptions deserve separate evaluation.

[Original source](https://arxiv.org/abs/2510.02332)

[Paper PDF](paper.pdf) · [Searchable text](paper.txt) · [Source page snapshot](source.html)

[Download provenance and checksums](metadata.json). Reported results were not reproduced here.

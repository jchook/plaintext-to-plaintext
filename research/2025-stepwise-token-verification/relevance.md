# Addressing Tokenization Inconsistency in Steganography and Watermarking Based on Large Language Models

EMNLP 2025. Reviewed 2026-10-18.

A direct implementation candidate: filters token choices whose detokenization and retokenization would diverge. Could retain more useful choices than our broad prefix-free filtering. The official Consistency repository includes roundtrip experiments.

Filtering changes the reference distribution. Its correctness argument does not remove numerical discrepancies between sender and receiver runtimes.

[Original source](https://aclanthology.org/2025.emnlp-main.361/) · [Implementation](https://github.com/ryehr/Consistency)

[Paper PDF](paper.pdf) · [Searchable text](paper.txt) · [Source page snapshot](source.html) · [Upstream README snapshot](upstream-readme.md) · [Repository page snapshot](repository.html)

[Download provenance and checksums](metadata.json). Reported results were not reproduced here.

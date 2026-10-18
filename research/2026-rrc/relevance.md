# Efficient Provably Secure Linguistic Steganography via Range Coding (RRC)

ACL 2026. Reviewed 2026-10-18.

A leading direct comparison for our interval coder. Reports approximately 100% entropy utilization and 3.57 bits/token on Llama-2-7B. Its repository documents precision, termination, and tokenization failures that matter for a real text-only protocol.

Utilization is supported empirically, not by a rigorous optimality proof. Message length is agreed in advance. Repository tests report 100% recovery from token IDs but about 91% from retokenized text for one 128-bit setting, and require matched inference environments.

[Original source](https://aclanthology.org/2026.acl-long.39/) · [Implementation](https://github.com/ryehr/RRC_steganography)

[Paper PDF](paper.pdf) · [Searchable text](paper.txt) · [Source page snapshot](source.html) · [Upstream README snapshot](upstream-readme.md) · [Repository page snapshot](repository.html)

[Download provenance and checksums](metadata.json). Reported results were not reproduced here.

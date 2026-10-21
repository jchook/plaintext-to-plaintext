# 000: Embedding sketches

Status: archived, incomplete. Preserved from `initial/` in the original commit
`ec98261`; the exact development date is not recorded.

## Question and approach

Could a geometric transformation of pretrained word vectors turn a sentence
into another meaningful sentence and support recovery with a key? The
[original concept](artifacts/README.md) describes that idea. The
[NumPy/GloVe sketch](artifacts/sketch-np.py),
[spaCy sketch](artifacts/sketch-spacy.py), and
[notebook](artifacts/Untitled.ipynb) preserve the attempted implementation.
The notebook checkpoint and empty `untitled` file are retained as well.

## Evidence and result

These are exploratory fragments. The spaCy script ends with an unfinished
expression; the GloVe script references an external local vector file and an
undefined `vec`. No saved authenticated round trip or byte-comparison result
demonstrates a working codec. This archive is not a runnable baseline.

## Decision and handoff

The later prototype uses a language model's conditional token probabilities
and an explicitly reversible arithmetic mapping. This gives a concrete decoding
procedure to test. The surviving notes do not establish exactly when that
design change was decided. Continue with the
[v1 experiment](../001-baseline-v1/README.md).

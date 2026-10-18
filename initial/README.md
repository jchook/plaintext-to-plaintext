# Plaintext-to-Plaintext Encryption

Imagine an encryption algorithm that converts a plain text paragraph into a different, meaningful plain text paragraph... and (with the right key) can convert it back again.

Imagine your government or corporate overlords wish to track your conversations and daily communication. Imagine your government wants to stop you from sending encrypted text, and even [classifies encryption tech as war munitions](https://en.wikipedia.org/wiki/Export_of_cryptography_from_the_United_States).

As they say, sometimes you can hide best in plain sight.

## How it works

Pretrained word embeddings provide us with a meaningful vectorization of sentence tokens. We can then use a simple mapping between two vector spaces, and generate a new sentence based on a simple geometric translation of the vectors.

Another method, we can simply map one language space to another language space.

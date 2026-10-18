# Perniciosa Vulpis

Meteor steganography library and CLI.

Based on the paper
[Meteor: Cryptographically Secure Steganography for Realistic Distributions](https://eprint.iacr.org/2021/686)
by Kaptchuk, Jois, Green, and Rubin.

Encodes arbitrary ciphertext into a sequence of natural-language tokens
using arithmetic coding over a language model distribution, and decodes
it back with bit-exact fidelity.

## Build

```sh
cmake -B build -S .
cmake --build build -j
ln -sf build/compile_commands.json .
```

The build requires x86-64. CMake will hard-fail on other architectures.

## Bundled models

The CLI can run with either a deterministic mock model (the default, no extra
setup) or a bundled Llama 3.2 model.

Two GGUF files are supported:

| Size | File | SHA-256 | Use |
|---|---|---|---|
| 1B | `third_party/models/Llama-3.2-1B-Instruct-Q5_K_M.gguf` | `69dce91345442121eb3195370337eefa02cf076c7d84bd39adc0ce9552ccdfef` | default |
| 3B | `third_party/models/llama-3.2-3b-instruct-q5_k_m.gguf` | `782f6d3246312ebfc5b3db83f2beaf5abf4371311206e9dc2c57703b564f55a0` | higher-quality cover text |

The CLI `--backend llama` defaults to the 1B model.  Use `--model` to
select the 3B model explicitly for higher-quality cover text.

### llama.cpp submodule

| Property | Value |
|---|---|
| Path | `third_party/llama.cpp` |
| Pinned commit | `0754b7b6fe6109909786bdaa763111167b7410c8` |

Pull both after cloning:

```sh
git submodule update --init --recursive
```

### Deployed layout

After `cmake --install build --prefix /usr/local`:

```
/usr/local/bin/perniciosavulpis-cli
/usr/local/share/perniciosavulpis/Llama-3.2-1B-Instruct-Q5_K_M.gguf
```

Both files must be present for `--backend llama` to work.

## Usage

### Mock backend (default)

Encode 5 bytes (`Hello` = `48656c6c6f`) into words:

```sh
$ build/cli/perniciosavulpis-cli encode \
    --wordlist words.txt \
    --seed deadbeefcafebabe \
    --input 48656c6c6f
outage skids schuss cayenne carpel franchisee whorls rays epithets extradites blowtorch specie Baal indicted disproportionately inamorata
```

Decode the words back to the original bytes:

```sh
$ build/cli/perniciosavulpis-cli decode \
    --wordlist words.txt \
    --seed deadbeefcafebabe \
    --words "outage skids schuss cayenne carpel franchisee whorls rays epithets extradites blowtorch specie Baal indicted disproportionately inamorata"
48656c6c6f
```

Self-test round-trip at a given bit count:

```sh
$ build/cli/perniciosavulpis-cli roundtrip --seed deadbeefcafebabe --bits 1024
bits in: 1024
bits out: 1024
tokens: 142
bits/token: 7.211
|K-K'|: 0
```

### Llama backend

Encode a file into cover text, then decode it back:

```sh
# Create a file to encode:
echo "secret message" > /tmp/input.txt

# Encode → cover text (natural-language output):
build/cli/perniciosavulpis-cli encode --backend llama \
    --input /tmp/input.txt --output /tmp/cover.txt \
    --prompt "Continue this story:"

# Take a look at the encoded message:
cat /tmp/cover.txt
Here follows the conversation recorded by the tape in the American Historical Press recording, recording number 12711 of April 17, 1947. The conversation in the room:  **Pulitzer reporter James

# Decode cover text → recovered file:
build/cli/perniciosavulpis-cli decode --backend llama \
    --words --input /tmp/cover.txt --output /tmp/recovered.txt \
    --prompt "Continue this story:"

# Verify:
diff /tmp/input.txt /tmp/recovered.txt   # must be identical
```

The same works with hex input and inline cover text:

```sh
# Encode 5 bytes (hex) → cover text to stdout:
build/cli/perniciosavulpis-cli encode --backend llama \
    --input 48656c6c6f --prompt "Continue this story:"

# Decode inline cover text → hex to stdout:
build/cli/perniciosavulpis-cli decode --backend llama \
    --words "the cover text from encode" --prompt "Continue this story:"
```

Specify model path and logit quantization explicitly:

```sh
build/cli/perniciosavulpis-cli encode --backend llama \
    --model /path/to/model.gguf --logit-bits 10 \
    --input /tmp/input.txt --output /tmp/cover.txt \
    --prompt "Continue this story:"
```

## Tests

### C tests

```sh
ctest --test-dir build --output-on-failure
```

Runs the arithmetic coder, distribution quantization, Meteor framing
round-trip tests, and the llama smoke test (skipped if the model is not
present).

The smoke test uses the **1B model by default** for fast iteration (~12 s
total for two loads + three inferences on a single core).  To test against
the 3B model instead:

```sh
cmake -B build -S . -DPV_TEST_MODEL_SIZE=3B
cmake --build build -j
ctest --test-dir build --output-on-failure
```

### Python statistical tests

Requires `pytest` and `hypothesis`:

```sh
pip install pytest hypothesis
```

Run from the repository root (the CLI must be built first):

```sh
python3 -m pytest tests/statistical/ -v
```

## Retokenization filter

BPE tokenization is not bijective: some token sequences detokenize to text
that retokenizes to a different token sequence.  This breaks the decode
pipeline when the receiver only has the cover text - the receiver tokenizes
the text, gets a different token sequence, and decode fails.

When `--backend llama` is selected, the encoder applies a **retokenization
filter** at each generation step.  For each candidate token (top-k by
probability, default k=64), the encoder:

1. Constructs the candidate text: detokenize(context + candidate).
2. Retokenizes that text.
3. Checks whether the retokenized prefix matches the original context +
   candidate.  If not, the token is marked unsafe and its probability is set
   to zero.

The decoder performs the identical filter, so both sides operate on identical
distributions.

### Wire format

**Cover text** is now the canonical wire format.  The receiver only needs the
cover text and the prompt to decode - no out-of-band token metadata is
required.  Token sequences can still be transmitted directly for debugging or
performance, but the text roundtrip is supported and reliable.

Encode produces cover text:

```sh
build/cli/perniciosavulpis-cli encode --backend llama \
    --input /tmp/input.txt --output /tmp/cover.txt \
    --prompt "Continue this story:"
```

Decode from cover text:

```sh
build/cli/perniciosavulpis-cli decode --backend llama \
    --words --input /tmp/cover.txt --output /tmp/recovered.txt \
    --prompt "Continue this story:"
diff /tmp/input.txt /tmp/recovered.txt   # must be identical
```

### Bandwidth

The retokenization filter reduces the model's effective per-token entropy -
typically by 10–30% depending on the prompt and model - because some tokens
are filtered out at each step.  This means the cover text is somewhat longer
per ciphertext byte than the unfiltered model would produce.

### Configuration

The `top_k` truncation parameter is load-bearing for performance: it limits
the number of tokenizer roundtrip calls per step from the full vocabulary
(~128k for Llama 3.2) to 64.  The retokenization filter is controlled by
`pv_truncation_params.retokenization_filter` (default off; enabled
automatically by the CLI when `--backend llama` is selected).

## Sentence completion

By default, encoding stops as soon as all ciphertext bits have been consumed
by the arithmetic coder.  This often produces cover text that ends
mid-sentence, which looks unnatural.

When `pv_truncation_params.sentence_completion` is enabled (the CLI sets it
automatically for `--backend llama`), the encoder continues generating tokens
greedily (argmax from the model distribution) after the data-carrying tokens
until a sentence-ending token is emitted (one containing `.`, `?`, `!`, or
`\n`).  A safety cap of 128 extra tokens prevents runaway generation.

The extra tokens carry no hidden data.  The decoder does not need any special
handling: the frame header is self-delimiting (it encodes the exact payload
length), so the decoder processes all tokens, recovers the frame, extracts
the payload, and ignores the surplus bits produced by the padding tokens.

This is fully compatible with multi-turn conversations: both parties see the
complete cover text (including the sentence ending) and use it as context for
subsequent turns.

## Multi-turn conversations (library API)

The CLI is a single-shot tool, but the library API supports multi-turn
conversations where two parties take turns encoding and decoding messages
within a shared, growing context - producing a continuous "story" that
carries hidden payloads in both directions.

The key is the `prompt` / `prompt_len` parameter on `pv_meteor_encode` and
`pv_meteor_decode`.  Each turn, both sides pass the accumulated context
(initial prompt + all previous cover-text tokens) as the prompt for the
next call.

### Example: two-turn exchange

```
Shared setup (both sides):
  pv_model *model = pv_llama_model_create("model.gguf", logit_bits);
  pv_truncation_params trunc = { 64, 1.0, 1.0, 1 };
  pv_token_id prompt[] = { /* tokenize("Continue this story:") */ };
  size_t prompt_len = /* ... */;
```

**Turn 1 - Alice sends to Bob:**

```c
// Alice encodes msg1 into cover-text tokens:
pv_meteor_encode(model, &trunc, prompt, prompt_len,
                 msg1, msg1_bits, tokens1, &n1);

// Alice detokenizes tokens1 → cover text, sends it to Bob.

// Bob retokenizes the received cover text → tokens1
// (retokenization filter guarantees this reproduces the same tokens).
// Bob decodes:
pv_meteor_decode(model, &trunc, prompt, prompt_len,
                 tokens1, n1, &msg1, &msg1_bits);
```

**Turn 2 - Bob replies to Alice:**

```c
// Both sides build the new context:
//   new_prompt = prompt || tokens1
size_t new_prompt_len = prompt_len + n1;
memcpy(new_prompt, prompt, prompt_len * sizeof(pv_token_id));
memcpy(new_prompt + prompt_len, tokens1, n1 * sizeof(pv_token_id));

// Bob encodes msg2 with the extended context:
pv_meteor_encode(model, &trunc, new_prompt, new_prompt_len,
                 msg2, msg2_bits, tokens2, &n2);

// Bob detokenizes tokens2 → cover text, sends it to Alice.

// Alice retokenizes, decodes with the same new_prompt:
pv_meteor_decode(model, &trunc, new_prompt, new_prompt_len,
                 tokens2, n2, &msg2, &msg2_bits);
```

Subsequent turns follow the same pattern: append the previous turn's tokens
to the prompt and call encode or decode.

### Why this works

- The `pv_model` is created once and reused across calls - no per-turn
  initialization.
- The KV cache is cleared on every `next_dist_raw` call, so there is no
  leaked state between turns.  The result depends only on
  `(model, context_tokens)`, and both sides pass identical contexts.
- The retokenization filter guarantees that cover text retokenizes to the
  original token sequence, so both sides reconstruct identical contexts
  from the transmitted text.

### Performance note

Clearing the KV cache every call means the full prompt is re-evaluated from
scratch each turn.  For turn N the context length is the initial prompt plus
all previous cover-text tokens, so inference cost grows with conversation
length.  This is correct but not yet optimized - a future improvement could
reuse the KV cache for the shared prefix.

## Determinism

The llama backend is deterministic within the following scope:

- **Architecture**: x86-64 only (the CMake build hard-fails elsewhere).
- **Build invariants**: identical compiler, identical flags (`-march=x86-64-v2
  -ffp-contract=off`), identical submodule commit.
- **Logit quantization**: sender and receiver must use the same
  `--logit-bits` value (default 10).

### Cross-machine verification

1. Build on machine A, run `ctest`. The smoke test writes
   `build/tests/reference/llama_smoke_dist.bin`.
2. Commit that file (it is ~1 MB and checked into git).
3. Build on machine B, run `ctest`. The smoke test compares against the
   reference file. A mismatch indicates a determinism bug.

The reference file encodes the raw softmax probability array (128 256 × 8
bytes = ~1 MB) produced by a fixed three-token context with
`logit_quantization_bits = 10`.

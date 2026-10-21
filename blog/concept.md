# Plaintext as ciphertext

The system encrypts a message, then represents the encrypted bytes as plausible
prose. Six pieces are needed to understand the construction:

1. There are two separate texts. The **message** is what we want to recover. The
   **cover** is what we transmit. Their meanings can be unrelated; recovery must
   preserve the message's exact bytes.
2. The transformer supplies a probability table. Given a fixed prompt and the
   cover generated so far, it scores possible next tokens. The model's weights
   stay unchanged. Our code chooses which token to emit from that table.
3. Choosing a token can communicate bits. If four equally likely continuations
   are assigned `00`, `01`, `10`, and `11`, emitting one communicates two bits.
   The receiver needs to know which continuations were available and their
   assignments.
4. Real token probabilities are unequal. Assigning equal-length bit strings to
   all candidates would ignore those probabilities. Arithmetic coding gives us
   a probability-aware mapping: it assigns tokens ranges of numbers, with wider
   ranges for more likely tokens. Successive choices narrow the range and reveal
   more bits. The numerical example below shows how.
5. The receiver reconstructs the choices as it reads. It runs the same model on
   the same cover prefix and rebuilds the same mapping, including its keyed
   ordering. Observing the next token tells it which range the sender selected.
   Both sides run ordinary forward passes through the transformer. Exact recovery
   requires agreement on the candidate tokens and their integer probabilities.
6. Conventional encryption supplies secrecy. We encrypt before choosing any
   cover tokens. The resulting packet of encrypted bytes and decoding metadata
   is called a **frame**. The shared key supports encryption and determines the
   ordering of token ranges. The model sees only the cover prompt and cover
   tokens; neither the secret message nor the key file enters its context.

The complete path is:

```text
Sender:   message bytes -> encrypt -> frame -> encode as text -> cover
Receiver: cover -> decode from text -> frame -> decrypt -> message bytes
```

Here, encoding and decoding mean converting between bits and cover text. Both
operations use the pretrained language model to compute next-token probabilities.

In our prototype, this message:

```text
The enemy planted a bomb in the belfry -- be CAREFUL!
```

became a journal entry beginning:

> Today was one of those days where everything felt just right. I woke up early,
> before the sun was fully up, and crept into the bathroom to start the water for
> my shower.

The [complete cover text](../experiments/001-baseline-v1/runs/verified/belfry.cover.txt) contains 2,635 bytes.
A separate decoding process recovered the original 53 bytes, including the
punctuation and capitalization. It needed the cover, the shared key, and the same
model and protocol. It had no record of the encoder's decisions.

We begin by encrypting the original message bytes. The prototype derives separate
encryption and interval-ordering keys from the complete key file using
HKDF-SHA256. ChaCha20-Poly1305 encrypts the message together with its length and
padding, using a fresh random nonce. The nonce and authenticated ciphertext form
the frame that the text codec embeds. The other derived key determines the order
of candidate intervals at each step. The language layer is a form of
steganography: it carries the encrypted data in choices that read as prose.

We used the complete text of *Alice's Adventures in Wonderland* as the demo key.
This exercises the file-based interface, but the book is public: anyone with the
same file and setup can decode the examples. A key derivation function cannot
create secrecy from a known book. A private random key provides secrecy without
needing hundreds of kilobytes of material.

A pretrained autoregressive transformer already gives us the interface we need:

$$
p_\theta(t_i \mid P, t_1, \ldots, t_{i-1})
$$

Here, $P$ is a shared prompt and the preceding tokens are the cover generated so
far. In the prototype, the prompt asks for an ordinary journal entry. We use
Llama 3.2 3B with its existing weights.

Attention, feed-forward layers, and the final softmax produce the next-token
distribution as usual. We take control at the sampling step. One way to sample
from a categorical distribution is to draw a uniform number in $[0,1)$ and use
the cumulative probabilities to select a token. We use the same partition into
ranges, but choose the number from the encrypted frame.

Suppose the cover ends with `I went out to buy`, and the next-token distribution
is this invented, simplified example:

| Token | Probability | Interval |
| --- | ---: | --- |
| ` milk` | 1/2 | [0, 1/2) |
| ` bread` | 1/4 | [1/2, 3/4) |
| ` coffee` | 1/4 | [3/4, 1) |

We partition the unit interval in proportion to the probabilities. A number
$x = 0.60$ selects ` bread`. Anyone who observes that token and knows the table
can infer that $x$ lies between $1/2$ and $3/4$. In binary, those numbers begin
with `0.10`, so that choice communicates the bits `10`.

After emitting ` bread`, we ask the transformer for the next distribution.
Suppose it now gives ` and` and `.` probability $1/2$ each. We split the selected
interval, $[1/2,3/4)$, into two equal parts:

| Next token | Subinterval |
| --- | --- |
| ` and` | [1/2, 5/8) |
| `.` | [5/8, 3/4) |

The same $x = 0.60$ selects ` and`. The receiver can now place $x$ in
$[1/2,5/8)$, whose numbers begin with `0.100` in binary. Reading ` bread and`
has revealed three bits. We continue subdividing the current interval using
each new distribution. This is arithmetic coding used to turn bits into text.

For a finite message, we need a precise stopping rule. Let the encrypted frame
contain $n$ bits, and let $b$ be its value as an unsigned integer. Retaining $n$
lets us recover any leading zeros. Those bits identify the interval

$$
J_b = \left[\frac{b}{2^n}, \frac{b+1}{2^n}\right).
$$

The encoder chooses $x$ strictly inside $J_b$ and emits tokens until the interval
identified by the cover lies entirely inside $J_b$. At that point, all numbers
consistent with the cover have the same first $n$ binary digits. Those digits
are the encrypted frame. The receiver never needs to recover the particular
point $x$.

This gives a short proof of recovery. Both sides start with the same interval
and prompt. Assume they have reconstructed the same token prefix. If they
compute the same ordered probability table, the next visible token identifies
the same subinterval on both sides. By induction, their intervals agree after
every token. The encoder's stopping condition then guarantees recovery of the
frame's exact bits.

The prototype makes the interval calculations exact by converting probabilities
into positive integer counts totaling 65,536 and using integer arithmetic for
the interval endpoints. Provided each step supplies at least two candidates,
each interval shrinks by a factor of at most 65,535/65,536. Since $x$ is strictly
inside $J_b$, continued subdivision must eventually fit inside it. A practical
encoder can still hit its work limit before that happens.

The probability table also needs to survive conversion from token IDs to visible
text. Decoding the cover with the model's usual tokenizer need not reproduce the
token IDs that generated it: different token sequences can spell the same bytes.
Our prototype therefore chooses candidate pieces such that no piece is a prefix
of another. For example, it cannot offer both ` a` and ` apple` at the same step.
The receiver can then identify the next chosen token by reading the cover bytes
against the reconstructed candidate table.

We select those pieces from the model's top 64 candidates, keeping printable,
valid UTF-8. The selected probabilities are renormalized and converted to integer
counts. Both sides apply the same rules. This restricts the available choices,
but makes the transmitted text sufficient to recover the token sequence without
a sidecar file.

Frames occupy multiples of 32 bytes. As the decoder recovers bits, it tries
authentication at those boundaries. Successful authentication identifies the
frame length; the encrypted length field identifies the original message within
the padding. The encoder also appends a deterministic sentence-completion
suffix, which the decoder reproduces and checks.

The model receives only the journal prompt and the evolving cover. The belfry
warning never enters its context. A refusal to discuss that warning therefore
does not arise during this encoding process. The model's training still affects
which cover continuations it considers plausible.

The recovery proof depends on agreement between the encoder's and decoder's
probability tables. In an abstract transformer with fixed weights, inference
mode, and fixed arithmetic, the forward pass is a function. Sampling randomness
is separate from that function. The KV cache stores intermediate attention
state; this scheme uses it in the usual way and does not hide the payload there.

Actual runtimes can evaluate the same prefix through different numerical paths.
Batching, hardware kernels, and cache reuse can change floating-point results.
Matching the most likely token is insufficient: the interval coder needs the
same integer probability table. Rounding the probabilities helps only when the
differences do not cross a rounding boundary or change candidate selection.

Our prototype uses a pinned model file and a dedicated inference process with a
controlled cache reset and request sequence. We verified recovery in separate
encoder and decoder processes, and recovered a saved cover after restarting the
inference server. These checks establish behavior for the tested configuration.
The proof explains what agreement guarantees; the checks establish whether the
runtime meets that assumption. We have not established compatibility across
arbitrary devices or tested the system on a phone.

The cost is substantial expansion. A token can occupy several bytes of visible
text while carrying only a fraction of a byte of hidden information. With
probability-preserving interval coding, a choice of probability $q$ narrows the
interval by that factor and contributes $-\log_2 q$ bits of information. A token
with probability 0.9 contributes about 0.15 bits. An almost inevitable word
offers almost no room to encode a choice.

For an ideal sampler, the expected information per step is the entropy of the
distribution used by the coder:

$$
H(q) = -\sum_t q(t)\log_2 q(t).
$$

That distribution includes our filtering and renormalization. Vocabulary size
alone does not determine capacity; the probabilities matter.

The [recorded runs](../experiments/001-baseline-v1/verification.json) show both the framing overhead and
the cost of expressing those bits as prose:

| Message | Original bytes | Frame bytes | Cover bytes | Expansion |
| --- | ---: | ---: | ---: | ---: |
| `The key is 12345` | 16 | 64 | 1,608 | 100.5x |
| Belfry warning | 53 | 96 | 2,635 | 49.7x |

The warning's 768-bit frame required 579 payload tokens, an effective rate of
about 1.3 frame bits per token. Completing the final sentence brought the cover
to 588 tokens. The full encode and decode each took about 30 seconds on the
tested CPU setup.

There is room to reduce overhead and improve candidate selection. Prompts that
allow more varied continuations may provide more capacity while retaining
readable prose. Flattening the distribution can increase capacity, but can hurt
fluency. These changes need measurement; the current expansion ratios
are observations from the prototype, not theoretical lower bounds.

Readable cover also does not establish that an observer cannot detect an encoded
message. In the ideal interval construction, a uniform random point selects
tokens in proportion to their interval widths. Our finite frame, finite random
tail, filtering, and stopping rule depart from that ideal. Authentication
protects the recovered message, but it makes no promise about the cover's
statistical resemblance to ordinary writing.

The prototype has demonstrated exact recovery for the example messages, Unicode
and mixed whitespace, and an empty input. It rejected the tested wrong-key and
altered-cover cases. Its next useful benchmark is how many cover bytes it needs
per recovered message byte at an acceptable level of fluency, under a decoding
configuration that both parties can reproduce.

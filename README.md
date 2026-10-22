# Plaintext to plaintext

This experimental codec encrypts a message, then carries the encrypted bytes in
model-generated prose. The receiver uses the key and the same model and protocol
to recover the original bytes exactly.

## Input and output

Here is a real round trip from the public-opening experiment.

Input message (16 bytes):

```text
The key is 12345
```

Transmitted stegotext (1,422 bytes):

> Hi Alex, it was great meeting you at the conference and hearing how your team is
> approaching the product launch. I'm going to ask Shannon to coordinate a conversation
> between your head of product and our research lead so we can compare notes on the
> questions we discussed. In the meantime, I wanted to follow up on a couple of points
> from our conversation.
>
> Our discussion about the launch timeline was really helpful in shaking out some of the
> misunderstandings I had going into the conversation with my team. I am curious to
> understand better how your approach differs from ours, as we've had some mixed signals
> from some of our key stakeholders. How do you go about prioritizing features and
> handling the inevitable trade-offs with respect to market release vs. platform
> updates? Are there any particular metrics or benchmarks that you find useful in
> evaluating the effectiveness of your approach? Additionally, how do you handle the
> handover from research to development, particularly when it comes to testing and
> feedback loops? I'm looking for some practical advice on how to smooth out our own
> transition from discovery to delivery. For example, what kind of testing have you done
> on your pre-launch builds, and how do you collaborate with development to test and
> validate your research findings? I'm hoping to learn more about your process and see
> if there are any best practices that we can apply to our own work.

Recovered message (16 bytes, authenticated and byte-for-byte identical):

```text
The key is 12345
```

The first paragraph is a supplied public opening that sets the subject and voice.
The generated continuation carries the encrypted message; its meaning can be
unrelated to the input. The decoder reads the opening from the cover and rebuilds
the shared prompt without a per-message sidecar.

Exact saved files: [input](experiments/003-opening-paragraph/runs/pilot-20261021/key-message.opening-conference-followup-t1.2.1.input),
[stegotext](experiments/003-opening-paragraph/runs/pilot-20261021/key-message.opening-conference-followup-t1.2.1.cover.txt),
and [recovered bytes](experiments/003-opening-paragraph/runs/pilot-20261021/key-message.opening-conference-followup-t1.2.1.recovered).
This example uses the public Alice demonstration key, Llama 3.2 3B, and opening v1
at temperature 1.2. See the [full pilot results](experiments/003-opening-paragraph/README.md)
for other samples, sizes, and limitations.

## Run and verify

From the repository root:

```sh
python3 -m pip install -r poc/requirements.txt
python3 -m unittest discover -s poc -p 'test_*.py' -v
python3 experiments/verify.py
```

The tests use local test predictors. The archive check compares saved bytes and
hashes; it does not rerun model inference. To encode your own messages, follow the
[runtime setup](poc/README.md) and [public-opening commands](experiments/003-opening-paragraph/PROTOCOL.md).

## Project map

Start with [Experiments and directions](EXPERIMENTS.md) for the short history,
results, decisions, and next experiment.

| Location | Contents |
| --- | --- |
| [experiments/](experiments/) | Numbered experiments, handoff READMEs, inputs, covers, recovered bytes, and measurements |
| [poc/](poc/README.md) | Shared codec implementations, tests, runners, and public demonstration key |
| [research/](research/README.md) | Archived papers and implementation references; [findings](research/summary.md) |
| [blog/concept.md](blog/concept.md) | Explanation of the original v1 construction |

This prototype has demonstrated exact local recovery. Covers can still be verbose,
invent details, or lose track of recipient roles. Statistical detectability,
real email transport, phone performance, and compatibility across runtimes remain
open questions.

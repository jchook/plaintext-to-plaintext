# Preliminary assessment of opening-paragraph steering

The opening paragraph steered these samples toward the requested email topics.
It did not reliably preserve recipient roles or prevent invented conversational
history. Some continuations read like plausible draft emails, but they still
need review before anyone sends them.

This is a qualitative review by the Codex `protocol_tests` agent, performed on
the saved outputs during the 2026-10-21 pilot. It is not a human reader study,
does not assign human ratings, and does not measure steganalysis or detection
resistance. Quoted text below is unchanged generated continuation text.
No external factual verification was performed. References to invented details
mean that the supplied opening does not establish them; this review cannot
determine whether a similar event or claim would be true in a real conversation.

| Aspect | Preliminary observation |
| --- | --- |
| Genre and subject | All six seeded specimens remain on their opening's email topic. |
| Recipient continuity | STEM at 1.0 switches from addressing Priya to referring to her in the third person. |
| Conversational history | Conference samples assign unestablished earlier statements to Alex; STEM samples add unestablished draft details. |
| Verbosity | Several messages keep asking for feedback after a plausible stopping point. |
| Surface language | Seeded samples include awkward phrasing and questions ending with periods; controls include exaggerated imagery. |

## Selection and evidence

Before inspecting the paragraph outputs, the parent agent specified the first
repetition of the `paragraph` payload for conference, STEM, and history openings
at temperature 1.0, plus the warm control. We then fixed a supplementary
selection: the same three opening conditions at 1.2 and the varied control at
1.0. That produces the eight files below, regardless of their quality. The
reviewer had already seen early `key-message` outputs; this review was neither
blind nor independent of those early observations.

All eight selected runs report exact recovery in
[results.json](runs/pilot-20261021/results.json), and all eight have successful
encode/decode phases in [attempts.json](runs/pilot-20261021/attempts.json).
Opening text supplies context for this review; the judgments concern the
generated continuation, not the copied first paragraph. The controls have no
public opening.

| Selection | Saved cover |
| --- | --- |
| Primary: conference, 1.0 | [paragraph.opening-conference-followup-t1.0.1](runs/pilot-20261021/paragraph.opening-conference-followup-t1.0.1.cover.txt) |
| Primary: STEM, 1.0 | [paragraph.opening-stem-revision-t1.0.1](runs/pilot-20261021/paragraph.opening-stem-revision-t1.0.1.cover.txt) |
| Primary: history, 1.0 | [paragraph.opening-history-revision-t1.0.1](runs/pilot-20261021/paragraph.opening-history-revision-t1.0.1.cover.txt) |
| Primary: warm control, 1.2 | [paragraph.warm-auto.1](runs/pilot-20261021/paragraph.warm-auto.1.cover.txt) |
| Supplementary: conference, 1.2 | [paragraph.opening-conference-followup-t1.2.1](runs/pilot-20261021/paragraph.opening-conference-followup-t1.2.1.cover.txt) |
| Supplementary: STEM, 1.2 | [paragraph.opening-stem-revision-t1.2.1](runs/pilot-20261021/paragraph.opening-stem-revision-t1.2.1.cover.txt) |
| Supplementary: history, 1.2 | [paragraph.opening-history-revision-t1.2.1](runs/pilot-20261021/paragraph.opening-history-revision-t1.2.1.cover.txt) |
| Supplementary: varied control, 1.0 | [paragraph.varied-auto.1](runs/pilot-20261021/paragraph.varied-auto.1.cover.txt) |

The treatment changes the wrapper and supplies a topic-specific public opening
together. This pilot does not isolate the wrapper's contribution from the
opening's genre and subject. Comparing each opening condition with its
temperature-matched control avoids mixing temperatures, but one selected cover
per condition cannot establish a general quality difference. The full pilot
has only two repetitions per condition, with independent encrypted token paths.

## Conference follow-up

At 1.0, the continuation addresses Alex and uses ordinary product-development
language. A question such as “Do you think there's a way to quantify the impact
of user testing on the product's overall success” fits the broad topic. The
message stays in a professional email register throughout.

It also invents prior conversation and sender experience. “We've found that
implementing a more robust analytics framework has helped us make more informed
decisions down the line” asserts work that the opening never establishes.
“I also remembered that you mentioned using design thinking principles” assigns
a specific statement to Alex. The opening promises “a couple of points”, but
the continuation expands into three long paragraphs of questions about testing,
product readiness, and design thinking.

At 1.2, the topic remains product work, but the same problem appears: “You
mentioned that it's not possible to replicate exactly how the product will be
used in the field” invents Alex's earlier words. “Should we throw more money at
the problem or regroup and tighten things up?” introduces a stronger operational
choice than the opening supports. Questions sometimes end with periods,
including “What do you think.” The final paragraph answers part of the sender's
own question, making the requested response less clear.

## STEM revision note

At 1.0, the continuation stays on statistical models, uncertainty, and the
structure of a draft. It nevertheless loses the recipient relationship almost
immediately. The opening addresses Priya directly; the continuation says “it
makes more sense for Priya to think critically about each step of the process”,
then asks “Does Priya still think” and “Can she offer any feedback”. This reads
as if the sender is writing to someone else about Priya.

“Now that the model fit discussion precedes the explanation of uncertainty”
adds an ordering decision absent from the opening. “Does Priya still think that
the discussion of statistical testing relies too heavily on common assumptions”
also invents a particular earlier criticism.

At 1.2, the message retains the direct request for feedback and avoids that
third-person shift. It drifts toward a new data-quality argument, though, and
claims “I've included most of the revised section” without an identifiable
section following it. Its assertion that everything following unsound data
“goes to waste” is broad rather than a careful explanation of statistical
uncertainty. This specimen supports trying the genre;
it does not establish factual reliability for STEM exposition.

## History revision note

The 1.0 sample is the clearest of the three primary email examples in this
reviewer's judgment. It preserves the writer-to-Morgan relationship and develops
the single-journey framing: “the journey could start with the arrival in port”
leads into transactions, broader networks, and choices about narrative structure.
It presents the proposed additions as possibilities rather than claims about
actual historical evidence.

Its main weakness is repetition. After “Let me know of any suggestions”, it
continues with two more paragraphs requesting advice. It broadens into thematic
sections and sensory details without settling the original question about the
transition from one journey to the wider chapter.

At 1.2, the continuation remains an editorial note about the same chapter.
“Would it be more effective to place a biographical sketch” asks a useful
structural question. Other wording is strained: “this creates its narrative
while developing the different ways of using the historical material” and “Am I
still in track of the focus I started with”. The latter should presumably use
`on track`. Lower temperature therefore did not eliminate every weakness, and
higher temperature did not cause a topic failure in this example.

## Unseeded controls

The warm 1.2 control follows its requested unfamiliar-town narrative, with
complete sentences and a café scene. Several details recreate the exaggerated
tone that motivated this experiment: a lemon-shaped pin “seemed to vibrate with
her energy”, espresso flows “like dark liquid magic”, and the café grows tense
“as a string of dropped gloves found their way onto the doorstep.” The gloves
appear without an explanation for the tension.

The varied 1.0 control also stays in café-and-town fiction. “The Perky Scone” and
“Ruth's Ravishing Ruby” emphasize invented colorful details. A couple celebrating
a birthday “looked more like they were trying to escape their pasts”, although
the narrator has supplied no basis for that inference. Both controls show that
the older prompt continues to request and produce a different kind of text;
their fictional names are permitted by that prompt and are not themselves an
instruction violation.

## Next questions

Keep the public-opening interface for the next experiment. Topic steering and
exact recovery both worked in these selected examples, while the prose defects
are specific enough to test further. A new template version could explicitly
require first-person sender and second-person recipient references, and forbid
claims about earlier conversations, attachments, or completed work unless the
opening states them. These are proposed interventions, not demonstrated fixes.

Test the natural message ending separately. The codec can finish a sentence
after embedding the frame, but it does not decide when an email has made its
point. The saved history and conference examples repeatedly ask for advice or
add new discussion after a plausible close. Repeating the study with a new
template and reviewing all repetitions would help distinguish persistent
failures from individual token paths. Any claim about resistance to detection
requires a separate evaluation.

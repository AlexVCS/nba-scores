# Ask glossary

Shared vocabulary for Ask, the natural-language basketball search. Decisions
that change these terms are recorded as ADRs in `docs/adr/`.

Status: draft, being refined during the Ask design interview (2026-09-29).

## Terms

**Ask**
The natural-language search feature. A user types a basketball question; the
app answers it from NBA data, respecting spoiler settings.

**System One model**
A decision model that reads a *state* and answers typed *questions* with
probabilities. It never generates text and cannot call tools itself. Jev and
Laya are both System One models and share the `POST /v1/systemone` wire shape.

**Jev**
TypeSafe's hosted System One model. Pinned to `jev-1.13.0`, never an alias.
About 200 ms per question and $0.042 per million input tokens; output is free.
Context is 64k tokens per request. See `docs/ask-evaluation.md` on
`ask/reviewed-components`.

**Laya**
ConvAI Innovations' open-weights System One model (Apache 2.0, about 421M
parameters). Runs locally on CPU (`pip install laya`) or behind `laya-serve`,
which speaks the same `/v1/systemone` API as Jev. English context is only 512
tokens. Its base checkpoints are near chance zero-shot, so the reported accuracy
depends on fine-tuning.

Laya currently runs in development and evaluation only. Production runs Jev,
then Luna, until Laya is *promoted* (ADR 0007).

**Promotion**
Enabling a tier in production after it passes its evaluation gate on a frozen,
unseen set.

**Accepted-field precision**
Of the fields a tier accepts at its threshold, the share that are correct. The
tier gate requires at least 98% (ADR 0009).

**Coverage**
The share of fields a tier accepts instead of escalating. The tier gate
requires at least 30%.

**Guess**
A wrong answer rendered to the user. The system gate allows zero.

**Question types** (System One)
- *Choice*: pick one of up to 255 named options; returns a probability for each option.
- *Noul*: yes/no; returns one probability.
- *Score*: 2–10 ordered levels.

**Interpreter**
The component that turns a user question plus candidates into a typed
interpretation (`InterpreterAdapter`). Existing adapters are Jev and OpenAI
Responses (gpt-4.1-mini, GPT-6 Luna).

**Candidate lookup**
Deterministic Python that finds the possible teams, players, dates, seasons,
rounds, and game numbers in a question *before* any model call. System One
models may only choose among these candidates.

**Normalizer**
Turns an interpreter output into a validated `AskRequest`, or into a
clarify/unsupported/invalid result.

**Cascade**
The policy that decides whether to accept one interpreter's reading, fall back
to another, widen the candidate set, ask the user to clarify, or fail. The order
is Laya, then Jev, then GPT Luna (ADR 0002).

**Tier**
One interpreter's position in the cascade. Laya and Jev escalate field by field;
Luna handles the whole request in one call.

**GPT Luna**
OpenAI's GPT-6 Luna (or GPT-5.6 Luna), the last tier. It is generative, but Ask
restricts it to strict structured output over the same candidates.

**Tool**
A Python function with a typed signature that fetches, parses, and caches NBA
data from one source. A System One model chooses the tool and its arguments from
closed sets; Python executes it. Every tool has an answer template and a spoiler
classification. See ADR 0001.

**Source**
The website a tool fetched from: stats.nba.com (primary) or Basketball-Reference
(fallback only). Every answer records its source (ADR 0003).

**Fallback fetch**
A Basketball-Reference fetch made only when stats.nba.com fails or doesn't
cover the fact. It is rate-limited and cached. This is separate from the
interpreter cascade.

**Tool registry**
The closed set of tools presented to the router as Choice options.

**Tool family**
A group of related tools sharing a result type: game search, boxscore stat,
playoff series, postseason summary, player season stats, season leaders,
records, and team records (ADR 0004).

**Game-log index**
A local SQLite store of every league-wide player and team game log from
stats.nba. It is built offline, frozen for completed seasons, and refreshed
nightly for the current one. It serves counting-game and streak records
(ADR 0005).

**Record template**
One of the closed set of record query shapes (stat, threshold, comparison,
scope, ordering). A records question must match one, or it is `unsupported`.

**Coverage note**
The part of an answer that says which seasons a statistic exists for
(for example, three-pointers from 1979-80 onward).

**Asking is consent**
Submitting a question is consent to see its answer. Ask answers are never
hidden. The global spoiler preference still governs suggestions, typeahead,
clarification options, and every page outside Ask (ADR 0006).

**Consent boundary**
The moment of submission. Nothing that reveals a result may render before it.

**Evidence check**
A Noul asking whether a tool's parsed result actually answers the question.
When it fails, Ask returns a clarification or `not_found` instead of a guess.

**Outcome**
The terminal state of an Ask request: answered, `needs_clarification`,
`unsupported`, `not_found`, or `unavailable`.

## Avoid

- "Agent" for Jev or Laya. They cannot plan or call tools; Python orchestrates.
- "Answer generation" for System One output. Answers are rendered from templates.

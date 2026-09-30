# 2. Interpreter cascade: Laya, then Jev, then GPT Luna

Date: 2026-09-29
Status: accepted

## Context

ADR 0001 limits models to choosing among options that Python supplies. We have
three kinds of interpreter:

- Laya: local, free, about 30 ms. English context is 512 tokens, and it is weak zero-shot.
- Jev: hosted, about 200 ms, about $0.0001 per question. Its context is 64k tokens.
- GPT Luna (GPT-6 Luna, with GPT-5.6 Luna as an alternative): hosted, generative,
  2–4 s. It was the most accurate on the 43-case development run (26/26
  complete, versus Jev's 15/26). On the paired, exposed 80-case comparison
  (`docs/verification/ask-jev-luna-regression-2026-09-29.json`), Luna scored
  67/80 with **four guesses**, and Jev scored 48/80 with **zero guesses**
  (173 ms median, versus 2,402 ms). Jev's thresholds were uncalibrated.

We want Jev and Laya to handle as much traffic as possible. The 80-case result
supports that goal: Jev's misses were escalations, not wrong answers. That is
exactly what a first tier should do.

## Decision

Each request escalates through a three-tier cascade:

1. **Laya.** Asks each field's decision locally and accepts fields whose
   confidence meets Laya's calibrated threshold. It skips any decision whose
   state exceeds 512 tokens.
2. **Jev.** Handles only the fields Laya did not accept, with its own
   calibrated threshold.
3. **GPT Luna.** Runs when fields remain unresolved after Jev. It fills the whole
   interpretation in one call through strict structured output over the same
   candidate IDs and enums. Like the other tiers, it only chooses; it never writes
   prose or calls tools (ADR 0001).

If all tiers leave a field unresolved or ambiguous, Ask asks the user to clarify.
It never guesses.

Laya and Jev escalate field by field. Luna works per request, because one Luna call
returns every field.

## Consequences

- Each tier needs thresholds calibrated on exposed development data. The current
  Jev thresholds are uncalibrated placeholders.
- A tier is enabled only after it passes its own evaluation gate. A tier that
  hasn't passed is skipped, not trusted.
- Diagnostics record the tier that decided each field, so we can measure how much
  traffic stays on Laya and Jev.
- Laya adds a local model dependency: roughly 800 MB of weights and CPU inference
  in the FastAPI process or a sidecar `laya-serve`.
- This supersedes the provisional "GPT-6 Luna alone" choice in
  `docs/ask-evaluation.md`.
- The production adapter factory instantiates only OpenAI today. Wiring the
  cascade requires code, not a change to `ASK_PARSER_MODEL`.
- Luna's four guesses mean the last tier also needs a veto, such as a normalizer
  cross-check or a Jev disagreement check, before the zero-guess system gate
  (ADR 0009) can pass.

# 8. Laya: evaluate the published checkpoint, then distill

Date: 2026-09-29
Status: accepted

## Context

Laya must pass its evaluation gate before promotion (ADR 0007). Its base
checkpoints are near chance zero-shot. The published fine-tuned checkpoint was
trained on generic typed decisions, not basketball.

## Decision

1. **Published checkpoint first.** Evaluate the published fine-tuned checkpoint,
   unchanged, on the development set. If it passes the gate on the frozen unseen
   set, promote it.
2. **Distill if it misses.** Build a training set from:
   - hand-labeled development questions;
   - Jev and Luna field decisions the normalizer accepted and the evaluation
     marked correct;
   - synthetic paraphrases generated per tool and per field.

   Fine-tune Laya locally on that set, pin the resulting checkpoint, and evaluate it.
3. **The unseen release set is never training data.** Once a question has been
   used for training or threshold tuning, it moves to the development set, and a
   new unseen set must be written for the next gate.

## Consequences

- Laya's state must fit in 512 tokens. The fan-out pattern already keeps the
  state to `{"question": ...}` with one typed question per field; candidate
  criteria must stay short, too.
- Choices with many candidates (50 or more) are a known Laya weakness. Candidate
  lookup should prune before asking Laya, or escalate those fields straight to Jev.
- Check the provider terms before training on Luna or Jev outputs. OpenAI's
  terms restrict using outputs to develop competing models. A narrow in-app
  classifier is probably fine, but confirm before step 2. If in doubt, train only
  on hand labels and synthetic paraphrases.
- Checkpoints, training data, and the training script are versioned, so a
  promotion is reproducible.

# 1. Python orchestrates Ask; Jev and Laya only choose

Date: 2026-09-29
Status: accepted

## Context

We want Ask to use Jev and Laya whenever possible, and to fetch NBA stats from
websites to answer natural-language questions. Both models are System One models:
they answer typed Choice, Noul, and Score questions over a state. They cannot
generate text, plan, or call tools.

## Decision

Python owns the control flow. For each request it:

1. Runs candidate lookup to find the possible entities, dates, and seasons.
2. Asks a System One model to pick the tool (Choice over the tool registry).
3. Asks it to pick the tool's arguments (Choices over the lookup candidates).
4. Executes the tool, which fetches, parses, and caches website data.
5. Asks the model whether the fetched evidence answers the question (Noul).
6. Renders a templated answer that links to its source.

A "tool" is a Python function with a typed signature. Its arguments must come from
closed sets that Python has already produced. The models never produce free-form
values, URLs, or prose.

## Consequences

- Hallucinated facts are structurally impossible. Any wrong answer is a wrong
  *choice*, and evaluations can score it per field.
- Every tool needs an answer template and a spoiler classification. Nothing is
  answerable until both exist.
- Questions that need open-ended synthesis are out of scope unless a later ADR
  adds a generative step.
- Jev and Laya stay interchangeable behind the shared `/v1/systemone` shape.

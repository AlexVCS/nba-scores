# Unseen evaluation authorship, September 29, 2026

I authored 100 new questions and labels in the isolated worktree at `/private/tmp/ask-reviewed-components`. The frozen production revision is `6cdae70d2589e14c65f899555f8311b513c1c213`. I did not inspect previous questions, fixtures, evaluation reports, prompts, candidate logic, interpreter implementations or normalizer implementations. I did not run candidate lookup, data providers or interpretation providers. I did not inspect prior material for overlap; the parent agent performs that check before running the evaluation.

I read the contract files `server/ask/models/common.py`, `server/ask/models/request.py` and `server/ask/models/interpreter.py`. From `server/ask/eval/runner.py`, I extracted only the `LabeledCase` class and its serialization method using Python's AST. I read `server/ask/data/player_catalog.json` for player identities and career intervals, and `server/ask/data/franchise_history.json` for dated franchise identities. The parent supplied a neutral data export of GameLocation values at `/private/tmp/ask-unseen-two-city-reference.json`; I copied those location values without examining location implementation. I also applied the unslop writing skill as instructed.

Each row has a question, explicit timezone-aware reference time, context, expected action, applicable request or reason, coverage tags and a short label rationale. The reference time appears at the top level for `LabeledCase.from_json`. Context contains only page context fields. No row contains hand-built candidates or alternate acceptable actions. The rationales explain the user's meaning, including why a missing or ambiguous selector needs clarification.

There are 25 cases associated with each request family.

| Family | Accept | Clarify | Unsupported |
| --- | ---: | ---: | ---: |
| game_search | 18 | 5 | 2 |
| boxscore_stat | 11 | 12 | 2 |
| playoff_series | 18 | 4 | 3 |
| postseason_summary | 18 | 4 | 3 |
| Total | 65 | 25 | 10 |

Coverage tags overlap. There are 12 ambiguous-player cases, 24 historical-franchise cases and 24 nickname cases. The player clarifications include 11 shared surnames and one shared first name, with contemporaneous alternatives recorded in each rationale. Venue questions distinguish where a game was played from which franchise participated. Nickname controls have dated era context. Missing-date and missing-season cases use unambiguous franchises, so the temporal selector is the only missing information. Two accepted questions describe a franchise through its former home while requesting games involving that franchise; the former city does not become a venue filter. Other cases cover page context, explicit overrides, year and week boundaries, a leap day, seven-day ranges, percentage team totals and supported playoff-series selector forms.

I validated all 100 rows through `LabeledCase.from_json`, including accepted-request schema validation. Additional checks passed for unique IDs, unique questions, the 300-character question limit, timezone-aware reference times, required counts and absence of embedded candidates. All accepted game-search date ranges fit the seven-day contract. Historical team names and abbreviations follow franchise history; location values preserve the neutral export verbatim. These are interpretation labels, so an unambiguous supported question remains accepted even if data retrieval would find no matching game or postseason participation.

Fixture: `server/tests/ask/fixtures/eval/unseen-two-2026-09-29.json`

SHA256: `fa3e001b816baf38967fd88c837b6228f2336af811749f06499cd4b59c1cf040`

Before any provider run, the parent supplied case IDs and category-level audit feedback. It supplied no prior question text or provider outputs. I replaced `unseen-two-boxscore_stat-24` after a reported overlap, replaced three undated Hornets questions with single-missing-selector questions, and revised `unseen-two-game_search-01` and `unseen-two-game_search-05` to cover former-home clauses. I also removed the duplicated reference time from each context object. The revised 100 cases pass the same schema and count checks. No prior evaluation material was opened during revision.

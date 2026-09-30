# Independent Ask evaluation authorship

I authored 100 questions and their expected labels in an independent agent context on September 29, 2026. The frozen production commit supplied for this work was `9291237869342615c2f3e7005d9d4ccaa61ca116`.

The fixture is `server/tests/ask/fixtures/eval/unseen-2026-09-29.json`. Its SHA-256 is `fd774408c30889239ff297baaabf2b971b73e5210bfa5b842fdfe478a1d37332`.

I did not read earlier evaluation questions, reports, failure analyses, prompts, candidate lookup code, or interpreter implementation. I read AGENTS.md, the request/common/interpreter model schemas, and only the LabeledCase schema and serialization section of the evaluation runner. I used player_catalog.json and franchise_history.json for authoritative entity references. The parent separately authorized a neutral city/home-tenure data export at `/private/tmp/ask-city-reference-2026-09-29.json`; it contained location values only.

I wrote every question and expected label before seeing interpreter outputs. I made no model or provider calls. Labels reflect the questions' meaning without adapting to implementation behavior. Every case fixes reference_time, and no case embeds hand-built candidates. No previously authored evaluation questions were exposed to this author. The parent will check duplicate overlap separately before release execution.

| Associated request family | Accept | Clarify | Unsupported | Total |
| --- | ---: | ---: | ---: | ---: |
| Game search | 20 | 4 | 1 | 25 |
| Boxscore statistic | 20 | 3 | 2 | 25 |
| Playoff series | 18 | 4 | 3 | 25 |
| Postseason summary | 17 | 4 | 4 | 25 |
| Total | 75 | 15 | 10 | 100 |

Coverage includes absolute dates, relative days and weeks, New York midnight, leap day, a year-spanning range, the seven-day limit, team and player aliases, historical franchise names, city filters, page context, explicit context overrides, missing details, and entity ambiguity. Accepted requests include player lines, team totals, game leaders, league postseason summaries, and team postseason summaries.

Offline validation used `LabeledCase.from_json` for all 100 cases and checked unique IDs, unique question text, the 300-character question limit, and the absence of embedded candidates. All checks passed. No production files changed, and I made no git commit or push. Beads tracking and the release evaluation belong to the parent task.

Before any live execution, the parent reported no exact duplicates against 470 prior questions and a near match for case099. I replaced case099 with a fresh career question without seeing the prior material. I also replaced cases075 and083 to give each a single missing detail, and added the explicitly named target team to game.teams in cases062,066,070,074,078. This corrects the serialization convention without changing the requested statistics. Counts remain 75 accept, 15 clarify, and 10 unsupported. I repeated all offline validation checks after these revisions; they passed. No provider outputs were exposed to the author.

The parent also identified season-boundary ambiguity in September for the phrase last season. I moved cases020 and063 to fixed November 3, 2026 reference times, retaining the expected 2025-26 season. This places those questions within the next active NBA season. All 100 labels still pass LabeledCase.from_json validation.

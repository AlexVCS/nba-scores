#!/usr/bin/env python3
"""Offline ADR 0009 tier gate for a frozen unseen Ask evaluation (nba-scores-kzc.3, #210).

Scores each gated tier's preserved per-field readings from a release journal against
field-level gold. It makes no provider calls and never reruns the evaluation. Gated
tiers come from the frozen manifest configuration: Laya when `laya_base_url` is set,
then Jev. Luna is the final tier and is reported for information only.

Gold comes from two sources:

* Mechanical: derived from the frozen fixture labels without judgment. Accept labels
  pin every field their intent reads, except `player` in non-player boxscore scopes
  (the request ignores it). Unsupported labels whose reason only an interpreter can
  produce pin the intent.
* Labeled: everything else, from an isolated labeler's file (see the set's
  field-label brief, e.g. docs/verification/ask-unseen-three-field-label-brief.md).

Fields Python decides are not tier readings and get no gold: `aggregation` for the
measured tools (server/ask/measure.py, QUESTION_TIER "question"), and `location` and
`target_team` when lookup found no mention (LOOKUP_DECIDED, field tier "lookup").
`limit` and career `view` are read by Python and are not interpreter fields.

Label schemas fix the field definitions. Schema 1 is the four-family definition the
unseen-two report was scored with; schema 2 covers all eight ADR 0004 tools.

Commands:

* `inventory --fixture PATH | --report PATH`: count gold fields by source, field and
  family. With a report, verifies the frozen inputs and separates lookup-decided fields.
* `template --fixture PATH --out PATH`: write the labeling template from the fixture alone.
* `score --report PATH --labels PATH --out PATH`: verify frozen hashes, score, write the
  report. The manifest comes from the report's `manifest_file`, the fixture from the
  manifest's `cases_file`, the journal from `journal_file` (or the report path with a
  `.jsonl` suffix); `--manifest`, `--fixture` and `--journal` override them.

The recorded unseen-two report (docs/verification/ask-unseen-two-2026-09-29-tier-gate.json)
reproduces, apart from `generated_at`, with:

    python scripts/ask/tier_gate.py score \\
        --report docs/verification/ask-unseen-two-2026-09-29.json \\
        --labels docs/verification/ask-unseen-two-2026-09-29-field-labels.json --out OUT

Its inventory: `inventory --label-schema 1 --report docs/verification/ask-unseen-two-2026-09-29.json`.

Field definition, acceptance and correctness rules are in `RULES_V1`/`RULES_V2` below
and in the report. Outputs are created exclusively; existing files are never overwritten.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, get_args

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.ask.config import FROZEN_CASCADE  # noqa: E402
from server.ask.eval.runner import LabeledCase  # noqa: E402
from server.ask.interpreters.tiered import LOOKUP_DECIDED  # noqa: E402
from server.ask.measure import MEASURED_INTENTS, QUESTION_TIER  # noqa: E402
from server.ask.models.candidates import CandidateLookupResult  # noqa: E402
from server.ask.models.common import DateComponents, Intent, SeasonType, StandingsScope, Stat  # noqa: E402
from server.ask.models.interpreter import InterpreterField, UnsupportedReason  # noqa: E402
from server.ask.normalize import RELEVANT_FIELDS, reference_date, resolve_components  # noqa: E402

PLAYER_CATALOG = "server/ask/data/player_catalog.json"
FRANCHISES = "server/ask/data/franchise_history.json"

# The second unseen set. Its manifest and strict report pin the fixture and manifest.
# Neither records the journal or report hash, so those two are pinned to commit 377001f,
# which added them. Later release.py reports record the journal hash themselves.
UNSEEN_TWO = {
    "fixture": "server/tests/ask/fixtures/eval/unseen-two-2026-09-29.json",
    "manifest": "docs/verification/ask-unseen-two-2026-09-29-manifest.json",
    "journal": "docs/verification/ask-unseen-two-2026-09-29.jsonl",
    "report": "docs/verification/ask-unseen-two-2026-09-29.json",
}
KNOWN_PINS = {
    UNSEEN_TWO["fixture"]: "fa3e001b816baf38967fd88c837b6228f2336af811749f06499cd4b59c1cf040",
    UNSEEN_TWO["manifest"]: "f188b8440715a4d0f15c58c92cf647dd815bf37db362febace1a29bebb47ca4e",
    UNSEEN_TWO["journal"]: "c43d1b9c99e3fbb917d9808a27873365c38dae83b2ed08a3ab53d513b6059fd4",
    UNSEEN_TWO["report"]: "30e142e3f4f81c8348008fa8e9ab58de9f09a9a4fa8e45e12c68f1b649c27a01",
}

PRECISION_MIN = 0.98
COVERAGE_MIN = 0.30
# Scorer choice, not ADR text: a pass is provisional when one more accepted-field
# error would fail precision, or coverage is below this. scripts/ask/release.py uses it too.
PROVISIONAL_COVERAGE = 0.35

# Closed-set fields select literal values; candidate-backed fields select candidate IDs.
CLOSED = {"intent", "stat_scope", "stat", "aggregation", "season_type", "standings_scope"}
CANDIDATE_SET = {"player": "player", "teams": "team", "target_team": "team", "date": "date", "season": "season",
                 "round": "round", "game_number": "game_number", "location": "location"}
STAT_SCOPES = {"player", "team", "leaders"}
AGGREGATIONS = {"total", "per_game"}
SEASON_TYPES = set(get_args(SeasonType))
STANDINGS_SCOPES = set(get_args(StandingsScope))
ROUNDS = {"first_round", "conference_semifinals", "conference_finals", "finals"}
CONFERENCES = {"east", "west", None}
UNSUPPORTED_REASONS = set(UnsupportedReason.__args__)
STATUSES = {"value", "absent", "ambiguous", "unresolved", "unlisted"}
UNLISTED_FIELDS = {"player", "teams", "target_team", "location"}
# Normalizer defaults: an absent read stands for this value.
ABSENT_DEFAULTS = {"aggregation": "total", "season_type": "regular_season", "standings_scope": "league"}

RULES_V1 = [
    "A field is one interpreter field (intent plus the fields RELEVANT_FIELDS assigns to the gold "
    "intent) on one question. Unsupported gold intent has only the intent field.",
    "location is excluded when its candidate set is not_mentioned: lookup decides it and no tier reads it.",
    "Jev accepts a reading when its confidence is at least 0.85, whatever its status "
    "(selected, absent, ambiguous or no_matching_candidate), as TieredAdapter does.",
    "A Jev 'unsupported' outcome is an accepted intent reading 'unsupported:<reason>'. The cascade "
    "accepts it at the adapter's unsupported_min (0.6) and the trace keeps no confidence.",
    "Fields with no Jev reading (Jev unavailable, or an unsupported outcome) are not accepted.",
    "Correctness is judged per reading against gold: selected values map through the recorded "
    "candidates to IDs/values; absent must match absent; ambiguous must match ambiguous; "
    "no_matching_candidate is correct for unlisted gold, or when no recorded candidate carries the gold value.",
    "An absent reading on a candidate-backed field counts as the page value when the set holds exactly "
    "one app_context candidate (the normalizer fills it).",
    "aggregation absent equals total; stat absent equals stat_line unless the gold scope is leaders "
    "(normalizer defaults). Teams compare as sets of franchise IDs; round compares round and conference.",
    "Later-tier vetoes and overrides are ignored: the tier is scored on its own readings (ADR 0009). "
    "A later tier's unsupported outcome replaces an accepted Jev intent in the cascade; Jev's reading "
    "is still scored as accepted.",
]

RULES_V2 = [
    "A field is one interpreter field (intent plus the fields RELEVANT_FIELDS assigns to the gold "
    "intent) on one question, for all eight ADR 0004 tools. Unsupported gold intent has only the intent "
    "field. target_team is a boxscore_stat field only when the gold stat_scope is team (relevant_fields).",
    "Fields Python decides are not tier readings and are excluded: aggregation for player_season_stats, "
    "season_leaders and career_stats (measure.py replaces the interpreter's read; field tier 'question'), "
    "and location and target_team when their candidate set is not_mentioned (field tier 'lookup'). "
    "limit, requested_limit and the career view are read by Python and are not interpreter fields.",
    "A gated tier accepts a reading when its confidence is at least the tier's frozen accept_min, whatever "
    "its status (selected, absent, ambiguous or no_matching_candidate), as TieredAdapter does. The first "
    "gated tier is scored on every field; a later gated tier on the fields earlier gated tiers escalated.",
    "A tier 'unsupported' outcome is an accepted intent reading 'unsupported:<reason>'. The cascade "
    "accepts it at the adapter's unsupported_min (0.6) and the trace keeps no confidence.",
    "Fields with no reading from the tier (tier unavailable, or an unsupported outcome) are not accepted.",
    "Correctness is judged per reading against gold: selected values map through the recorded "
    "candidates to IDs/values; absent must match absent; ambiguous must match ambiguous; "
    "no_matching_candidate is correct for unlisted gold, or when no recorded candidate carries the gold value.",
    "An absent reading on a candidate-backed field counts as the page value when the set holds exactly "
    "one app_context candidate (the normalizer fills it).",
    "Normalizer defaults: aggregation absent equals total (boxscore_stat); season_type absent equals "
    "regular_season; standings_scope absent equals league; stat absent equals stat_line for boxscore_stat "
    "outside leaders scope, player_season_stats, and career_stats with a player. Teams compare as sets of "
    "franchise IDs; round compares round and conference.",
    "On season_leaders and all-time career lists a stat_line read equals an absent stat (the normalizer "
    "asks which statistic for both).",
    "A team-scope boxscore with one named team also accepts an absent target_team (the normalizer takes "
    "the lone team as the target), and an absent teams read when the tier's target_team read is that team "
    "(the normalizer takes the target as the game's team).",
    "When lookup expansion reran the cascade, a tier is scored on its last attempt, against the "
    "candidates that attempt read.",
    "Unsupported gold is mechanical only for reasons no Python rule produces; multi_game_average, "
    "unsupported_leader_stat and other (normalizer and season-scope guards) need a labeled intent.",
    "Later-tier vetoes and overrides are ignored: the tier is scored on its own readings (ADR 0009). "
    "A later tier's unsupported outcome replaces an accepted earlier intent in the cascade, and a later "
    "absent read replaces an accepted no_matching_candidate on a field lookup found no text for; the "
    "earlier reading is still scored as accepted.",
]

SCOPE_LIMITS_V1 = [
    "Four of the eight ADR 0004 tool families are present; championships and the other families "
    "have no questions, so per-family gate evidence covers four families only.",
    "Laya is disabled; only Jev can be gated.",
    "Jev 'unsupported' outcomes carry no confidence; the cascade accepts them at unsupported_min 0.6, "
    "below accept_min 0.85.",
    "Field gold for clarification, some unsupported and non-player boxscore cases was labeled after "
    "the run by an isolated labeler; the fixture's authoring isolation does not cover those labels.",
    "Journal and report hashes were not registered before the run; they are pinned to commit 377001f.",
    "In the cascade, a later tier's unsupported outcome discards an accepted Jev intent without a veto, "
    "so tier-level and system-level intent credit can differ.",
]


@dataclass(frozen=True)
class Profile:
    """Field definitions a label schema fixes."""

    label_schema: str
    intents: tuple[str, ...]
    fields: tuple[str, ...]
    # Unsupported reasons a Python rule can produce; an interpreter may read such a
    # question as a supported intent with an unsupported parameter, so it needs a label.
    normalizer_unsupported: frozenset[str]
    rules: tuple[str, ...]
    question_bucket: bool  # report the Python-decided aggregation fields in the inventory


V1 = Profile("ask-tier-gate-field-labels/1",
             ("game_search", "boxscore_stat", "playoff_series", "postseason_summary"),
             ("intent", "stat_scope", "stat", "aggregation", "player", "teams", "date", "season", "round",
              "game_number", "location"),
             frozenset({"multi_game_average", "unsupported_leader_stat"}), tuple(RULES_V1), False)
V2 = Profile("ask-tier-gate-field-labels/2", get_args(Intent), get_args(InterpreterField),
             frozenset({"multi_game_average", "unsupported_leader_stat", "other"}), tuple(RULES_V2), True)
PROFILES = {p.label_schema: p for p in (V1, V2)}
LABEL_SCHEMA = V2.label_schema


@dataclass(frozen=True)
class TierSpec:
    name: str
    model: str | None
    accept_min: float

    def show(self) -> dict[str, Any]:
        return {"name": self.name, "model": self.model, "accept_min": self.accept_min}


def gated_tiers(config: dict[str, Any]) -> list[TierSpec]:
    """Gated tiers in cascade order from a frozen configuration (ADR 0009: Laya, Jev)."""
    tiers = []
    if config.get("laya_base_url"):
        if "laya_accept_min" not in config:
            raise IntegrityError("Laya is enabled but the configuration records no laya_accept_min")
        tiers.append(TierSpec("laya", config.get("laya_model"), config["laya_accept_min"]))
    tiers.append(TierSpec("jev", config["jev_model"], config["jev_accept_min"]))
    return tiers


class IntegrityError(ValueError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- gold values ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Gold:
    status: str  # value | absent | ambiguous | unresolved | unlisted
    value: Any = None  # canonical, hashable
    reason: str | None = None  # unresolved dates
    alternatives: tuple = ()

    def show(self) -> dict[str, Any]:
        out: dict[str, Any] = {"status": self.status}
        if self.status == "value":
            out["value"] = _show(self.value)
        if self.reason:
            out["reason"] = self.reason
        if self.alternatives:
            out["alternatives"] = [_show(a) for a in self.alternatives]
        return out


def _show(value: Any) -> Any:
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, tuple):
        return [_show(v) for v in value]
    if isinstance(value, dt.date):
        return value.isoformat()
    return value


def city_key(city: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", city.casefold()).split())


ABSENT = Gold("absent")


def question_decided(intent: str | None) -> list[str]:
    """Fields Python reads from the question text for this intent (never a tier reading)."""
    return ["aggregation"] if intent in MEASURED_INTENTS else []


def fields_for(intent: str, profile: Profile = V2, team_scope: bool = False) -> list[str]:
    """Gold fields of an intent: interpreter fields a tier decides, in profile order."""
    if intent == "unsupported":
        return ["intent"]
    skip = set(question_decided(intent))
    if not team_scope:
        skip.add("target_team")  # relevant_fields: only a team-scope question has a target team
    return [f for f in profile.fields if (f == "intent" or f in RELEVANT_FIELDS[intent]) and f not in skip]


@dataclass
class CasePlan:
    case_id: str
    family: str
    label_scope: str | None  # None (fully mechanical), "all", or "player"
    scored_intent: str | None = None  # an intent or "unsupported"; None until labeled
    gold: dict[str, list[Gold]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)  # field -> mechanical | labeled
    notes: dict[str, str] = field(default_factory=dict)
    profile: Profile = V2

    def team_scope(self) -> bool:
        return any(g.status == "value" and g.value == "team" for g in self.gold.get("stat_scope", []))

    def fields(self) -> list[str]:
        return fields_for(self.scored_intent or self.family, self.profile, self.team_scope())


def family_of(case_id: str, profile: Profile = V2) -> str:
    for family in profile.intents:
        if f"-{family}-" in case_id:
            return family
    raise IntegrityError(f"{case_id}: no family in id")


def _round(round_name: str | None, conference: str | None) -> Gold:
    return Gold("value", (round_name, conference)) if round_name else ABSENT


def request_gold(request: Any, profile: Profile = V2) -> tuple[dict[str, list[Gold]], list[str]]:
    """Mechanical gold for an accept label, plus fields the request leaves undetermined."""
    gold: dict[str, Gold | list[Gold]] = {"intent": Gold("value", request.intent)}
    undetermined: list[str] = []

    def teams(refs) -> Gold:
        return Gold("value", frozenset(t.team_id for t in refs)) if refs else ABSENT

    def team(ref) -> Gold:
        return Gold("value", frozenset({ref.team_id})) if ref else ABSENT

    def value(v) -> Gold:
        return Gold("value", v)

    intent = request.intent
    if intent not in profile.intents:
        raise IntegrityError(f"{intent} is not an intent of label schema {profile.label_schema}")
    if intent == "game_search":
        gold["date"] = value((request.dates.start, request.dates.end))
        gold["teams"] = teams(request.teams)
        gold["location"] = value(city_key(request.location.city)) if request.location else ABSENT
    elif intent == "boxscore_stat":
        game = request.game
        gold["stat_scope"] = value(request.scope)
        gold["stat"] = value(request.stat.stat)
        gold["aggregation"] = value(request.stat.aggregation)
        if request.scope == "player":
            gold["player"] = value(request.player.player_id)
        else:
            undetermined.append("player")
        if request.scope == "team":
            named = [t.team_id for t in game.teams]
            target = request.team.team_id if request.team else (named[0] if len(named) == 1 else None)
            if target is None:
                raise IntegrityError("team scope with no derivable target team")
            # With one named team the normalizer takes it as the target, so absent is equivalent.
            gold["target_team"] = [value(target)] + ([ABSENT] if named == [target] else [])
        gold["teams"] = teams(game.teams)
        gold["date"] = value((game.date, game.date)) if game.date else ABSENT
        gold["season"] = value(game.season) if game.season else ABSENT
        gold["round"] = _round(game.round, game.conference)
        gold["game_number"] = value(game.game_number) if game.game_number else ABSENT
    elif intent == "playoff_series":
        gold["season"] = value(request.season)
        gold["teams"] = teams(request.teams)
        gold["round"] = _round(request.round, request.conference)
    elif intent == "postseason_summary":
        gold["season"] = value(request.season)
        gold["teams"] = team(request.team)
    elif intent == "player_season_stats":
        gold["player"] = value(request.player.player_id)
        gold["teams"] = team(request.team)
        gold["season"] = value(request.season)
        gold["stat"] = value(request.stat.stat)
        gold["season_type"] = value(request.season_type)
    elif intent == "team_records":
        gold["teams"] = team(request.team)
        gold["season"] = value(request.season)
        gold["standings_scope"] = value(request.standings_scope)
        gold["season_type"] = value("regular_season")  # the tool answers regular seasons only
    elif intent == "season_leaders":
        gold["season"] = value(request.season)
        gold["stat"] = value(request.stat.stat)
        gold["season_type"] = value(request.season_type)
    elif intent == "career_stats":
        gold["player"] = value(request.player.player_id) if request.player else ABSENT
        gold["stat"] = value(request.stat.stat)
        gold["season_type"] = value(request.season_type)
    else:
        raise IntegrityError(f"no mechanical gold rule for {intent}")
    keep = set(fields_for(intent, profile, team_scope=getattr(request, "scope", None) == "team"))
    return {k: (v if isinstance(v, list) else [v]) for k, v in gold.items() if k in keep}, undetermined


def plan(case: LabeledCase, profile: Profile = V2) -> CasePlan:
    family = family_of(case.id, profile)
    if case.action == "accept":
        gold, undetermined = request_gold(case.request, profile)
        return CasePlan(case.id, family, "player" if undetermined else None, case.request.intent,
                        gold, {k: "mechanical" for k in gold}, profile=profile)
    if case.action == "unsupported" and case.unsupported_reason not in profile.normalizer_unsupported:
        return CasePlan(case.id, family, None, "unsupported",
                        {"intent": [Gold("value", f"unsupported:{case.unsupported_reason}")]},
                        {"intent": "mechanical"}, profile=profile)
    return CasePlan(case.id, family, "all", profile=profile)


# -- labels ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Reference:
    players: frozenset[int]
    teams: frozenset[int]

    @classmethod
    def load(cls, root: Path = ROOT) -> Reference:
        players = json.loads((root / PLAYER_CATALOG).read_text())["players"]
        franchises = json.loads((root / FRANCHISES).read_text())["franchises"]
        return cls(frozenset(row[0] for row in players), frozenset(f["team_id"] for f in franchises))


def _typed(field_name: str, raw: Any, ref: Reference, where: str) -> Any:
    def fail(msg: str):
        raise ValueError(f"{where}: {msg}: {raw!r}")

    if field_name == "stat_scope":
        return raw if raw in STAT_SCOPES else fail("unknown stat_scope")
    if field_name == "stat":
        return raw if raw in Stat.__args__ else fail("unknown stat")
    if field_name == "aggregation":
        return raw if raw in AGGREGATIONS else fail("unknown aggregation")
    if field_name == "season_type":
        return raw if raw in SEASON_TYPES else fail("unknown season_type")
    if field_name == "standings_scope":
        return raw if raw in STANDINGS_SCOPES else fail("unknown standings_scope")
    if field_name == "player":
        return raw if isinstance(raw, int) and raw in ref.players else fail("player_id not in player_catalog.json")
    if field_name in ("teams", "target_team"):
        return raw if isinstance(raw, int) and raw in ref.teams else fail("team_id not in franchise_history.json")
    if field_name == "date":
        try:
            start, end = dt.date.fromisoformat(raw["start"]), dt.date.fromisoformat(raw["end"])
        except (TypeError, KeyError, ValueError):
            fail("date needs ISO start and end")
        if end < start or (end - start).days >= 7:
            fail("date values span 1-7 days; use unresolved/range_too_long for longer")
        return (start, end)
    if field_name == "season":
        if not (isinstance(raw, str) and re.fullmatch(r"\d{4}-\d{2}", raw)
                and (int(raw[:4]) + 1) % 100 == int(raw[5:])):
            fail("season must look like 2015-16")
        return raw
    if field_name == "round":
        if not isinstance(raw, dict) or raw.get("round") not in ROUNDS or raw.get("conference") not in CONFERENCES:
            fail("round needs {round, conference}")
        return (raw["round"], raw.get("conference"))
    if field_name == "game_number":
        return raw if isinstance(raw, int) and 1 <= raw <= 7 else fail("game_number is 1-7")
    if field_name == "location":
        return city_key(raw) if isinstance(raw, str) and raw.strip() else fail("location is a city name")
    fail(f"unknown field {field_name}")


def parse_intent(raw: Any, where: str, profile: Profile = V2) -> str:
    if raw in profile.intents:
        return raw
    if isinstance(raw, str) and raw.startswith("unsupported:") and raw.split(":", 1)[1] in UNSUPPORTED_REASONS:
        return raw
    raise ValueError(f"{where}: intent must be an intent or unsupported:<reason>: {raw!r}")


def parse_one(field_name: str, raw: Any, ref: Reference, where: str, profile: Profile = V2) -> Gold:
    if not isinstance(raw, dict) or raw.get("status") not in STATUSES:
        raise ValueError(f"{where}: status must be one of {sorted(STATUSES)}")
    status = raw["status"]
    extra = set(raw) - {"status", "value", "alternatives", "reason", "note"}
    if extra:
        raise ValueError(f"{where}: unknown keys {sorted(extra)}")
    if field_name == "intent":
        if status != "value":
            raise ValueError(f"{where}: intent labels are values")
        return Gold("value", parse_intent(raw.get("value"), where, profile))
    if status == "value":
        if field_name == "teams":
            ids = raw.get("value")
            if not isinstance(ids, list) or not 1 <= len(ids) <= 2 or len(set(ids)) != len(ids):
                raise ValueError(f"{where}: teams value is a list of one or two team IDs")
            return Gold("value", frozenset(_typed("teams", i, ref, where) for i in ids))
        return Gold("value", _typed(field_name, raw.get("value"), ref, where))
    if status == "ambiguous":
        alts = raw.get("alternatives")
        if not isinstance(alts, list) or len(alts) < 2:
            raise ValueError(f"{where}: ambiguous needs at least two alternatives")
        return Gold("ambiguous", alternatives=tuple(_typed(field_name, a, ref, where) for a in alts))
    if status == "unresolved":
        if field_name != "date" or raw.get("reason") not in ("year_required", "range_too_long"):
            raise ValueError(f"{where}: unresolved is for dates, reason year_required or range_too_long")
        return Gold("unresolved", reason=raw["reason"])
    if status == "unlisted" and field_name not in UNLISTED_FIELDS:
        raise ValueError(f"{where}: unlisted applies to {sorted(UNLISTED_FIELDS)}")
    return Gold(status)


def parse_field(field_name: str, raw: Any, ref: Reference, where: str,
                profile: Profile = V2) -> tuple[list[Gold], str | None]:
    if isinstance(raw, dict) and "any_of" in raw:
        options, note = raw["any_of"], raw.get("note")
        if set(raw) - {"any_of", "note"} or not isinstance(options, list) or len(options) < 2:
            raise ValueError(f"{where}: any_of needs two or more labels")
        if not (isinstance(note, str) and note.strip()):
            raise ValueError(f"{where}: any_of needs a note")
        return [parse_one(field_name, o, ref, f"{where}[{i}]", profile) for i, o in enumerate(options)], note
    if raw is None:
        raise ValueError(f"{where}: not labeled")
    return [parse_one(field_name, raw, ref, where, profile)], None


def _plans_profile(plans: dict[str, CasePlan]) -> Profile:
    profiles = {p.profile for p in plans.values()}
    if len(profiles) > 1:
        raise IntegrityError("plans mix label schemas")
    return profiles.pop() if profiles else V2


def apply_labels(plans: dict[str, CasePlan], labels: dict[str, Any], ref: Reference) -> None:
    """Validate the labeler's file and merge it into the plans."""
    profile = _plans_profile(plans)
    if labels.get("schema") != profile.label_schema:
        raise ValueError(f"labels schema must be {profile.label_schema}")
    rows = {row["case_id"]: row for row in labels.get("cases", [])}
    needed = {cid for cid, p in plans.items() if p.label_scope}
    if set(rows) != needed:
        raise ValueError(f"labels must cover exactly the {len(needed)} template cases; "
                         f"missing {sorted(needed - set(rows))}, extra {sorted(set(rows) - needed)}")
    for cid, row in rows.items():
        p = plans[cid]
        fields = row.get("fields") or {}
        if p.label_scope == "player":
            if row.get("intent") is not None or row.get("scored_intent") is not None or set(fields) != {"player"}:
                raise ValueError(f"{cid}: label only `player` for this case")
        else:
            intent_options, note = parse_field("intent", row.get("intent"), ref, f"{cid}.intent", profile)
            scored = row.get("scored_intent")
            values = {g.value for g in intent_options}
            supported = {v for v in values if v in profile.intents}
            if scored not in (*profile.intents, "unsupported"):
                raise ValueError(f"{cid}: scored_intent must be an intent or 'unsupported'")
            if scored == "unsupported" and supported:
                raise ValueError(f"{cid}: a supported intent is acceptable; score its fields")
            if scored != "unsupported" and scored not in values:
                raise ValueError(f"{cid}: scored_intent must be one of the acceptable intents")
            team_scope = False
            if "stat_scope" in fields and scored == "boxscore_stat":
                scopes, _ = parse_field("stat_scope", fields["stat_scope"], ref, f"{cid}.stat_scope", profile)
                team_scope = any(g.status == "value" and g.value == "team" for g in scopes)
            expected = set(fields_for(scored, profile, team_scope)) - {"intent"}
            if set(fields) != expected:
                raise ValueError(f"{cid}: {scored} needs exactly fields {sorted(expected)}, got {sorted(fields)}")
            p.scored_intent = scored
            p.gold["intent"] = intent_options
            p.sources["intent"] = "labeled"
            if note:
                p.notes["intent"] = note
        for name, raw in fields.items():
            options, note = parse_field(name, raw, ref, f"{cid}.{name}", profile)
            p.gold[name] = options
            p.sources[name] = "labeled"
            if note:
                p.notes[name] = note


def label_warnings(cases: dict[str, LabeledCase], plans: dict[str, CasePlan]) -> list[str]:
    """Labels that disagree with the frozen clarification or unsupported label. Uses no traces."""
    warnings = []
    for cid, p in plans.items():
        case = cases[cid]
        if case.action == "clarify" and case.clarify_field == "intent" and p.profile.question_bucket:
            if case.clarify_reason == "ambiguous" and len(p.gold.get("intent", [])) < 2:
                warnings.append(f"{cid}: clarify intent/ambiguous labeled with one intent")
        elif case.action == "clarify" and case.clarify_field in p.gold:
            statuses = {g.status for g in p.gold[case.clarify_field]}
            if case.clarify_field == "teams":  # the normalizer reports target_team problems under teams
                statuses |= {g.status for g in p.gold.get("target_team", [])}
            want = {"missing": {"absent"}, "ambiguous": {"ambiguous"}, "year_required": {"unresolved"},
                    "range_too_long": {"unresolved"}, "no_matching_candidate": {"unlisted"}}.get(case.clarify_reason)
            if want and not statuses & want:
                warnings.append(f"{cid}: clarify {case.clarify_field}/{case.clarify_reason} labeled "
                                f"{sorted(statuses)}")
        elif (case.action == "clarify" and p.scored_intent and case.clarify_field not in p.gold
              and case.clarify_field not in question_decided(p.scored_intent)):
            warnings.append(f"{cid}: clarify field {case.clarify_field} is not a field of {p.scored_intent}")
        if case.action == "unsupported" and p.sources.get("intent") == "labeled":
            reason = f"unsupported:{case.unsupported_reason}"
            if not any(g.value == reason for g in p.gold["intent"]) and p.scored_intent == "unsupported":
                warnings.append(f"{cid}: unsupported reason differs from the frozen label")
    return warnings


# -- tier readings ---------------------------------------------------------------------------


@dataclass
class Scored:
    case_id: str
    family: str
    field: str
    source: str
    disposition: str  # accepted | escalated | not_escalated
    reading: dict[str, Any] | None
    confidence: float | None
    correct: bool | None  # judged for every reading, so later tiers can reuse it
    error_kind: str | None = None
    gold: list[Gold] = field(default_factory=list)


def _candidate_value(field_name: str, candidate) -> tuple[str, Any]:
    v = candidate.value
    if v.kind == "team":
        return "value", v.team.team_id
    if v.kind == "player":
        return "value", v.player.player_id
    if v.kind == "date":
        if v.resolved is None:
            return "unresolved", v.unresolved_reason
        return "value", (v.resolved.start, v.resolved.end)
    if v.kind == "season":
        return "value", v.season
    if v.kind == "round":
        return "value", (v.round, v.conference)
    if v.kind == "game_number":
        return "value", v.game_number
    return "value", city_key(v.location.city)


def effective(field_name: str, read: dict[str, Any] | None, cands: CandidateLookupResult,
              extracted: tuple[str, Any] | None = None) -> tuple[str, Any]:
    """(kind, payload) of a reading after the normalizer's page-context fill.

    kind is value | unresolved | absent | ambiguous | no_match | invalid.
    """
    status = read["status"] if read else "absent"
    if status == "absent" and field_name in CANDIDATE_SET:
        offered = cands.sets[CANDIDATE_SET[field_name]].candidates
        if len(offered) == 1 and offered[0].source == "app_context":
            read, status = {"status": "selected", "selected": [offered[0].id]}, "selected"
        elif field_name == "date" and extracted is not None:
            return extracted
    if status == "absent":
        return "absent", None
    if status == "ambiguous":
        return "ambiguous", tuple(read.get("alternatives", []))
    if status == "no_matching_candidate":
        return "no_match", None
    if field_name in CLOSED:
        return "value", read["selected"][0]
    values = []
    for cid in read["selected"]:
        candidate = cands.by_id(cid)
        if candidate is None or candidate.field != CANDIDATE_SET[field_name]:
            return "invalid", cid
        values.append(_candidate_value(field_name, candidate))
    if field_name == "teams":
        return "value", frozenset(v for _, v in values)
    return values[0]


# stat_default for season and all-time leaders lists: the normalizer asks which statistic
# for a stat_line read exactly as for an absent one (ADR 0011).
NO_STAT = "no_stat"


def _default(field_name: str, kind: str, payload: Any, stat_default: str | None) -> tuple[str, Any]:
    if field_name == "stat" and stat_default == NO_STAT and (kind, payload) == ("value", "stat_line"):
        return "absent", None
    if kind == "absent" and field_name == "stat" and stat_default == NO_STAT:
        return kind, payload
    if kind == "absent" and field_name in ABSENT_DEFAULTS:
        return "value", ABSENT_DEFAULTS[field_name]
    if kind == "absent" and field_name == "stat" and stat_default:
        return "value", stat_default
    return kind, payload


def _gold_default(field_name: str, gold: Gold, stat_default: str | None) -> Gold:
    kind, payload = _default(field_name, gold.status, gold.value, stat_default)
    if kind == "absent" and gold.status == "value":
        return ABSENT
    return Gold("value", payload) if kind == "value" and gold.status == "absent" else gold


def _representable(field_name: str, gold: Gold, cands: CandidateLookupResult) -> bool:
    """Whether some recorded candidate carries the gold value."""
    offered = [_candidate_value(field_name, c) for c in cands.sets[CANDIDATE_SET[field_name]].candidates]
    if gold.status == "unresolved":
        return ("unresolved", gold.reason) in offered
    if field_name == "teams":
        return gold.value <= {v for _, v in offered}
    return ("value", gold.value) in offered


def judge(field_name: str, kind: str, payload: Any, golds: list[Gold], cands: CandidateLookupResult,
          stat_default: str | None) -> tuple[bool, str | None]:
    kind, payload = _default(field_name, kind, payload, stat_default)
    golds = [_gold_default(field_name, g, stat_default) for g in golds]
    for gold in golds:
        if kind == "value" and gold.status == "value" and payload == gold.value:
            return True, None
        if kind == "unresolved" and gold.status == "unresolved" and payload == gold.reason:
            return True, None
        if kind in ("absent", "ambiguous") and gold.status == kind:
            return True, None
        if kind == "no_match" and (gold.status == "unlisted" or (
                gold.status in ("value", "unresolved") and field_name in CANDIDATE_SET
                and not _representable(field_name, gold, cands))):
            return True, None
    return False, f"{kind}_vs_{'|'.join(sorted({g.status for g in golds}))}"


def final_attempt(row: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """The tier records of the last cascade attempt, and the candidates that attempt read.

    Lookup expansion reruns the cascade on wider candidates, so a row can hold several
    attempts. Each record then carries its own candidates (release.py Recorder); journals
    written before that hold one attempt, read against the row's candidates."""
    outputs = row["tier_outputs"]
    # Every attempt starts at the cascade's first tier; a later attempt may stop earlier
    # than the one before it (jev, luna, then jev alone).
    start = max((i for i, r in enumerate(outputs) if r["tier"] == outputs[0]["tier"]), default=0)
    records: list[dict[str, Any]] = outputs[start:]
    if len(records) < len(outputs) and not all(r.get("candidates") for r in records):
        raise IntegrityError(f"{row['case_id']}: several attempts without per-attempt candidates")
    return records, next((r["candidates"] for r in records if r.get("candidates")), row["candidates"])


def _tier_record(row: dict[str, Any], tier: str) -> dict[str, Any] | None:
    return next((r["output"] for r in final_attempt(row)[0] if r["tier"] == tier), None)


def _target_names_lone_team(p: CasePlan, output: dict[str, Any], cands: CandidateLookupResult) -> bool:
    """Whether the tier read the lone named team as target_team. An absent `teams` read then
    builds the same request (Normalizer._target_team)."""
    gold = p.gold.get("target_team", [])
    read = next((f for f in output["fields"] if f["field"] == "target_team"), None)
    if ABSENT not in gold or read is None:
        return False
    return any(g.status == "value" and effective("target_team", read, cands, None) == ("value", g.value)
               for g in gold)


def stat_default(p: CasePlan) -> str | None:
    """What an absent stat read becomes in the normalizer for the gold intent, if anything."""
    intent = p.scored_intent
    leaders = any(g.status == "value" and g.value == "leaders" for g in p.gold.get("stat_scope", []))
    if intent == "career_stats":
        return "stat_line" if any(g.status != "absent" for g in p.gold.get("player", [])) else NO_STAT
    if intent == "season_leaders":
        return NO_STAT
    if leaders:
        return None
    return "stat_line"


def _extracted(output: dict[str, Any], cands: CandidateLookupResult, case: LabeledCase) -> tuple[str, Any] | None:
    raw = output.get("extracted_date")
    if raw is None or cands.sets["date"].status == "candidates":
        return None
    resolved = resolve_components(DateComponents.model_validate(raw), reference_date(case.context))
    if isinstance(resolved, str):
        return ("unresolved", resolved) if resolved != "invalid_date" else ("absent", None)
    return "value", (resolved.start, resolved.end)


def _lookup_decided(name: str, cands: CandidateLookupResult) -> bool:
    return name in LOOKUP_DECIDED and cands.sets[LOOKUP_DECIDED[name]].status == "not_mentioned"


def score_tier(tier: str, accept_min: float | None, cases: dict[str, LabeledCase], plans: dict[str, CasePlan],
               rows: dict[str, dict[str, Any]], *, only: set[tuple[str, str]] | None = None) -> list[Scored]:
    """Score one tier's readings. `accept_min=None` marks a final tier (every reading is final).
    `only` restricts scoring to (case_id, field) pairs, e.g. fields an earlier tier escalated."""
    out: list[Scored] = []
    for cid, p in plans.items():
        row = rows[cid]
        records, raw_candidates = final_attempt(row)
        cands = CandidateLookupResult.model_validate(raw_candidates)
        output = _tier_record(row, tier)
        later = [r["tier"] for r in records]
        escalates = tier in later and later.index(tier) < len(later) - 1
        for name in p.fields():
            if _lookup_decided(name, cands):
                continue  # decided by lookup (LOOKUP_DECIDED), never by a tier
            if only is not None and (cid, name) not in only:
                continue
            item = Scored(cid, p.family, name, p.sources[name], "not_escalated", None, None, None,
                          gold=p.gold[name])
            out.append(item)
            if output is None or output["outcome"] == "unavailable":
                item.disposition = "escalated" if escalates else "not_escalated"
                item.error_kind = "no_reading"
                continue
            if output["outcome"] == "unsupported":
                if name != "intent":
                    item.error_kind = "no_reading"
                    continue
                read, kind, payload = None, "value", f"unsupported:{output['unsupported_reason']}"
                item.reading = {"status": "selected", "selected": [payload]}
                accepted = True
            else:
                read = next((f for f in output["fields"] if f["field"] == name), None)
                if read is None and (name == "intent" or accept_min is not None):
                    item.disposition = "escalated" if escalates else "not_escalated"
                    item.error_kind = "no_reading"
                    continue
                extracted = _extracted(output, cands, cases[cid]) if name == "date" else None
                kind, payload = effective(name, read, cands, extracted)
                item.reading = {k: read[k] for k in ("status", "selected", "alternatives")} if read else {
                    "status": "absent"}
                item.confidence = read["confidence"] if read else None
                accepted = accept_min is None or (item.confidence is not None and item.confidence >= accept_min)
            if kind == "invalid":
                item.correct, item.error_kind = False, "invalid_candidate"
            else:
                item.correct, item.error_kind = judge(name, kind, payload, p.gold[name], cands, stat_default(p))
                if name == "teams" and kind == "absent" and _target_names_lone_team(p, output, cands):
                    item.correct, item.error_kind = True, None
            item.disposition = "accepted" if accepted else ("escalated" if escalates else "not_escalated")
    return out


def check_cascade(tier: str, accept_min: float, rows: dict[str, dict[str, Any]], scored: list[Scored]) -> None:
    """The acceptance rule must agree with which tier the frozen cascade credited (first tier only)."""
    by_key = {(s.case_id, s.field): s for s in scored}
    for cid, row in rows.items():
        output = _tier_record(row, tier)
        sets = final_attempt(row)[1]["sets"]
        final = row["attempts"][-1]["output"]["metadata"]["field_tiers"] if row["attempts"] else {}
        for name, decided_by in final.items():
            if decided_by == "lookup":
                if name not in LOOKUP_DECIDED or sets[LOOKUP_DECIDED[name]]["status"] != "not_mentioned":
                    raise IntegrityError(f"{cid}:{name} lookup-decided with candidates")
                continue
            if decided_by == QUESTION_TIER:
                # Python read it from the question (measure.py); no tier decided it, and a tier's
                # undecided read of it never escalates (TieredAdapter._complete).
                continue
            if output is None or output["outcome"] == "unavailable":
                if decided_by == tier:
                    raise IntegrityError(f"{cid}:{name} credited to {tier} without an output")
                continue
            read = None
            if output["outcome"] == "unsupported":
                accepted = name == "intent"
            else:
                read = next((f for f in output["fields"] if f["field"] == name), None)
                accepted = read is not None and read["confidence"] is not None and read["confidence"] >= accept_min
            if decided_by == tier and not accepted:
                raise IntegrityError(f"{cid}:{name} credited to {tier} below the threshold")
            # A later tier's unsupported outcome replaces every decision, including this
            # tier's accepted intent (TieredAdapter.interpret returns early without a veto).
            overridden = row["attempts"][-1]["output"]["outcome"] == "unsupported" and decided_by != tier
            # A later tier's absent read replaces a no-match on a field lookup found no text for
            # (TieredAdapter._unfounded_no_match).
            unfounded = (read is not None and read["status"] == "no_matching_candidate" and name in CANDIDATE_SET
                         and sets[CANDIDATE_SET[name]]["status"] == "not_mentioned")
            if decided_by not in (tier, "veto") and accepted and not overridden and not unfounded:
                raise IntegrityError(f"{cid}:{name} accepted by {tier} but credited to {decided_by}")
            item = by_key.get((cid, name))
            if item is not None and decided_by == tier and item.disposition != "accepted":
                raise IntegrityError(f"{cid}:{name} scorer disposition disagrees with the cascade")


# -- metrics ---------------------------------------------------------------------------------


def wilson_lower(successes: int, n: int, z: float = 1.959964) -> float | None:
    if n == 0:
        return None
    phat = successes / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return round((centre - margin) / denom, 4)


def metrics(items: list[Scored]) -> dict[str, Any]:
    eligible = len(items)
    accepted = [s for s in items if s.disposition == "accepted"]
    correct = sum(1 for s in accepted if s.correct)
    escalated = sum(1 for s in items if s.disposition == "escalated")
    return {
        "eligible": eligible,
        "accepted": len(accepted),
        "accepted_correct": correct,
        "accepted_errors": len(accepted) - correct,
        "precision": round(correct / len(accepted), 4) if accepted else None,
        "coverage": round(len(accepted) / eligible, 4) if eligible else None,
        "escalated": escalated,
        "escalation_rate": round(escalated / eligible, 4) if eligible else None,
        "not_accepted_not_escalated": eligible - len(accepted) - escalated,
    }


def gate(items: list[Scored]) -> dict[str, Any]:
    m = metrics(items)
    accepted, correct, eligible = m["accepted"], m["accepted_correct"], m["eligible"]
    precision_ok = accepted > 0 and correct * 100 >= PRECISION_MIN * 100 * accepted
    coverage_ok = eligible > 0 and accepted * 100 >= COVERAGE_MIN * 100 * eligible
    passed = precision_ok and coverage_ok
    # Additional accepted-field errors the precision threshold would still tolerate.
    slack = math.floor(correct - PRECISION_MIN * accepted + 1e-9) if accepted else None
    provisional = passed and (slack == 0 or accepted < PROVISIONAL_COVERAGE * eligible)
    return {**m, "precision_min": PRECISION_MIN, "coverage_min": COVERAGE_MIN,
            "precision_passed": precision_ok, "coverage_passed": coverage_ok, "passed": passed,
            "error_slack": slack, "precision_wilson95_lower": wilson_lower(correct, accepted),
            "provisional": provisional,
            "provisional_rule": f"pass with zero error slack or coverage below {PROVISIONAL_COVERAGE}"}


def breakdown(items: list[Scored], key: str, profile: Profile = V2) -> dict[str, Any]:
    order = profile.fields if key == "field" else profile.intents
    groups = {k: [s for s in items if getattr(s, key) == k] for k in order}
    return {k: metrics(v) for k, v in groups.items() if v}


def error_rows(items: list[Scored]) -> list[dict[str, Any]]:
    return [{"case_id": s.case_id, "field": s.field, "source": s.source, "reading": s.reading,
             "confidence": s.confidence, "gold": [g.show() for g in s.gold], "error_kind": s.error_kind}
            for s in items if s.disposition == "accepted" and not s.correct]


def inventory(plans: dict[str, CasePlan], rows: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Gold fields by source. Labeled cases' field counts depend on the labeled intent,
    so they are reported as the fields of the family's intent (an estimate)."""
    profile = _plans_profile(plans)
    buckets = ["mechanical", "labeled", "lookup_decided"] + (["question_decided"] if profile.question_bucket else [])
    counts: dict[str, dict[str, dict[str, int]]] = {b: {} for b in buckets}

    def add(bucket: str, family: str, name: str) -> None:
        fam = counts[bucket].setdefault(family, {})
        fam[name] = fam.get(name, 0) + 1

    for cid, p in plans.items():
        sets = rows[cid]["candidates"]["sets"] if rows is not None else None
        for name in p.fields():
            if sets is not None and name in LOOKUP_DECIDED and sets[LOOKUP_DECIDED[name]]["status"] == "not_mentioned":
                add("lookup_decided", p.family, name)
            elif p.sources.get(name) == "mechanical":
                add("mechanical", p.family, name)
            else:
                add("labeled", p.family, name)
        if profile.question_bucket:
            for name in question_decided(p.scored_intent or p.family):
                add("question_decided", p.family, name)
    totals = {bucket: sum(sum(f.values()) for f in fams.values()) for bucket, fams in counts.items()}
    out = {"by_bucket": counts, "totals": totals,
           "labeled_cases": sorted(cid for cid, p in plans.items() if p.label_scope),
           "note": "labeled counts assume each labeled case's family intent; the labeler may choose another"}
    if profile.question_bucket:
        out["field_notes"] = [
            "question_decided: aggregation for the measured tools is read by Python (measure.py), not a tier.",
            "labeled boxscore_stat cases are counted without target_team; it is a field only when the labeled "
            "stat_scope is team.",
        ]
        if rows is None:
            out["field_notes"].append(
                "No journal: location and target_team are counted under their gold source; with a journal, "
                "those whose candidate set is not_mentioned move to lookup_decided.")
    return out


# -- loading and verification ------------------------------------------------------------------


def rel(path: str | Path, root: Path = ROOT) -> str:
    """A path relative to the repository root when it is inside it (report keys stay stable)."""
    p = Path(path)
    resolved = (p if p.is_absolute() else Path.cwd() / p).resolve()
    try:
        return str(resolved.relative_to(root.resolve()))
    except ValueError:
        return str(resolved)


@dataclass(frozen=True)
class SetPaths:
    fixture: str
    manifest: str
    journal: str
    report: str


def resolve_paths(report: str, manifest: str | None = None, fixture: str | None = None,
                  journal: str | None = None, root: Path = ROOT) -> SetPaths:
    """Paths of one frozen run, from the release report unless given."""
    report = rel(report, root)
    doc = json.loads((root / report).read_text())
    manifest = rel(manifest, root) if manifest else doc["manifest_file"]
    if fixture is None:
        fixture = json.loads((root / manifest).read_text())["cases_file"]
    else:
        fixture = rel(fixture, root)
    if journal:
        journal = rel(journal, root)
    elif doc.get("journal_file"):
        journal = str(Path(report).parent / doc["journal_file"])
    else:
        journal = str(Path(report).with_suffix(".jsonl"))
    return SetPaths(fixture, manifest, journal, report)


def load_cases(fixture: str | Path, root: Path = ROOT) -> dict[str, LabeledCase]:
    raw = json.loads((root / fixture).read_text())["cases"]
    return {c["id"]: LabeledCase.from_json(c) for c in raw}


def load_rows(journal: str | Path, root: Path = ROOT) -> dict[str, dict[str, Any]]:
    rows = [json.loads(line) for line in (root / journal).read_text().splitlines() if line.strip()]
    return {row["case_id"]: row for row in rows}


def check_pins(hashes: dict[str, str], pins: dict[str, str]) -> None:
    changed = [path for path, sha in pins.items() if path in hashes and hashes[path] != sha]
    if changed:
        raise IntegrityError(f"frozen inputs changed: {changed}")


def verify(paths: SetPaths, root: Path = ROOT, pins: dict[str, str] = KNOWN_PINS) -> tuple[dict[str, str],
                                                                                          list[TierSpec]]:
    """Check the frozen fixture, manifest, journal and report agree. Returns their hashes
    and the gated tiers of the frozen configuration."""
    hashes = {path: digest(root / path) for path in (paths.fixture, paths.manifest, paths.journal, paths.report)}
    check_pins(hashes, pins)
    manifest = json.loads((root / paths.manifest).read_text())
    report = json.loads((root / paths.report).read_text())
    if manifest["cases_sha256"] != hashes[paths.fixture] or report["cases_sha256"] != hashes[paths.fixture]:
        raise IntegrityError("fixture hash differs from the manifest or report")
    if report["manifest_sha256"] != hashes[paths.manifest]:
        raise IntegrityError("manifest hash differs from the report")
    if "journal_sha256" in report:
        if report["journal_sha256"] != hashes[paths.journal]:
            raise IntegrityError("journal hash differs from the report")
    elif paths.journal not in pins:
        raise IntegrityError("the report records no journal hash and the journal is not pinned")
    config = manifest["configuration"]
    if "configuration" in report and report["configuration"] != config:
        raise IntegrityError("report configuration differs from the manifest")
    tiers = gated_tiers(config)
    cases, rows = load_cases(paths.fixture, root), load_rows(paths.journal, root)
    if list(cases) != list(rows) or [c["case_id"] for c in report["cases"]] != list(rows):
        raise IntegrityError("journal, report and fixture cases differ")
    first = tiers[0]
    for cid, row in rows.items():
        output = _tier_record(row, first.name)
        if output is None or (first.model and output["metadata"]["model"] != first.model):
            raise IntegrityError(f"{cid}: no {first.model or first.name} output")
    return hashes, tiers


def template(cases: dict[str, LabeledCase], fixture: str | None = None, fixture_sha256: str | None = None,
             profile: Profile = V2) -> dict[str, Any]:
    """The labeling template. Built from the fixture alone; carries no trace content."""
    items = []
    for cid, case in cases.items():
        p = plan(case, profile)
        if not p.label_scope:
            continue
        item = {"case_id": cid, "question": case.question,
                "reference_time": case.context.reference_time.isoformat(),
                "context": case.context.model_dump(mode="json", exclude={"reference_time"}, exclude_none=True),
                "label_scope": p.label_scope}
        if p.label_scope == "player":
            item.update({"fixed_intent": p.scored_intent, "intent": None, "scored_intent": None,
                         "fields": {"player": None}})
        else:
            item.update({"intent": None, "scored_intent": None, "fields": {}})
        item["notes"] = ""
        items.append(item)
    doc = {
        "schema": profile.label_schema,
        "fixture": fixture,
        "fixture_sha256": fixture_sha256,
        "labeler": {"name": "", "labeled_at": "", "isolation_statement": ""},
        "fields_by_intent": {intent: [f for f in fields_for(intent, profile, team_scope=True) if f != "intent"]
                             for intent in (*profile.intents, "unsupported")},
    }
    if profile is not V1:
        doc["field_conditions"] = {
            "target_team": "boxscore_stat only, and only when your stat_scope label is team; omit it otherwise"}
        doc["not_labeled"] = {
            "aggregation": sorted(i for i in profile.intents if question_decided(i)),
            "reason": "Python reads the measure from the question for these intents; it is not labeled here"}
    doc["cases"] = items
    return doc


def score(labels_path: Path, paths: SetPaths, root: Path = ROOT) -> dict[str, Any]:
    labels = json.loads(labels_path.read_text())
    profile = PROFILES.get(labels.get("schema"))
    if profile is None:
        raise ValueError(f"unknown labels schema {labels.get('schema')!r}; expected one of {sorted(PROFILES)}")
    hashes, tiers = verify(paths, root)
    if labels.get("fixture_sha256") != hashes[paths.fixture]:
        raise IntegrityError("labels were made for a different fixture")
    cases, rows = load_cases(paths.fixture, root), load_rows(paths.journal, root)
    plans = {cid: plan(case, profile) for cid, case in cases.items()}
    apply_labels(plans, labels, Reference.load())  # repository reference data, not part of the run
    return build_report(cases, plans, rows, hashes | {rel(labels_path, root): digest(labels_path)}, tiers,
                        pinned=[p for p in hashes if p in KNOWN_PINS and p in (paths.journal, paths.report)])


def _scope_limits(profile: Profile, plans: dict[str, CasePlan], tiers: list[TierSpec],
                  pinned: list[str]) -> list[str]:
    if profile is V1:
        return list(SCOPE_LIMITS_V1)
    present = [f for f in profile.intents if any(p.family == f for p in plans.values())]
    missing = [f for f in profile.intents if f not in present]
    limits = [f"{len(present)} of the {len(profile.intents)} ADR 0004 tool families have questions"
              + (f"; no questions for {', '.join(missing)}." if missing else ".")]
    if not any(t.name == "laya" for t in tiers):
        limits.append("Laya is disabled in the frozen configuration; only Jev can be gated.")
    limits += [
        "Tier 'unsupported' outcomes carry no confidence; the cascade accepts them at unsupported_min 0.6, "
        "below the tiers' accept_min.",
        "Field gold for clarification, some unsupported and non-player boxscore cases was labeled after "
        "the run by an isolated labeler; the fixture's authoring isolation does not cover those labels.",
        "aggregation for the measured tools, limit and the career view are decided by Python, not tiers; "
        "their correctness is part of the system gate only.",
    ]
    if pinned:
        limits.append(f"Hashes of {', '.join(pinned)} were not registered before the run; they are pinned "
                      "in scripts/ask/tier_gate.py.")
    limits.append("In the cascade, a later tier's unsupported outcome discards an accepted earlier intent without "
                  "a veto, so tier-level and system-level intent credit can differ.")
    return limits


def build_report(cases, plans, rows, hashes, tiers: list[TierSpec] | None = None,
                 pinned: list[str] | None = None) -> dict[str, Any]:
    profile = _plans_profile(plans)
    tiers = tiers if tiers is not None else gated_tiers(FROZEN_CASCADE)
    results: dict[str, Any] = {}
    only = None
    for index, spec in enumerate(tiers):
        scored = score_tier(spec.name, spec.accept_min, cases, plans, rows, only=only)
        if index == 0:
            check_cascade(spec.name, spec.accept_min, rows, scored)
        results[spec.name] = {
            "gate": gate(scored), "by_field": breakdown(scored, "field", profile),
            "by_family": breakdown(scored, "family", profile),
            "by_gold_source": {src: metrics([s for s in scored if s.source == src]) for src in ("mechanical", "labeled")},
            "accepted_field_errors": error_rows(scored)}
        if index > 0:
            results[spec.name]["eligible_rule"] = "fields earlier gated tiers escalated"
        only = {(s.case_id, s.field) for s in scored if s.disposition == "escalated"}
    luna = score_tier("luna", None, cases, plans, rows, only=only)
    luna_read = [s for s in luna if s.reading is not None]
    results["luna"] = {"informational": f"final tier, no confidences; readings on fields "
                                        f"{tiers[-1].name.capitalize()} escalated",
                       "fields": len(luna), "read": len(luna_read),
                       "correct": sum(1 for s in luna_read if s.correct),
                       "by_field": {k: {"read": len(v), "correct": sum(1 for s in v if s.correct)}
                                    for k in profile.fields if (v := [s for s in luna_read if s.field == k])}}
    if "laya" not in results:
        results["laya"] = {"informational": "disabled in the frozen configuration; no readings"}
    return {
        "purpose": "Offline ADR 0009 tier gate from preserved traces; no provider calls, no rerun",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs_sha256": hashes,
        "tier": tiers[0].show() if len(tiers) == 1 else [t.show() for t in tiers],
        "rules": list(profile.rules),
        "gold_inventory": inventory(plans, rows),
        "label_notes": {cid: p.notes for cid, p in plans.items() if p.notes},
        "label_warnings": label_warnings(cases, plans),
        "tiers": results,
        "scope_limits": _scope_limits(profile, plans, tiers, pinned or []),
    }


def write_exclusive(path: Path, doc: dict[str, Any]) -> None:
    with path.open("x") as out:
        out.write(json.dumps(doc, indent=1) + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    schema_help = "label schema: 2 covers all eight tools (default); 1 is the four-family unseen-two definition"
    i = sub.add_parser("inventory")
    i.add_argument("--fixture", help="fixture only: no journal, no verification")
    i.add_argument("--report", help="release report: verify the frozen run and use its journal")
    i.add_argument("--manifest")
    i.add_argument("--journal")
    i.add_argument("--label-schema", choices=("1", "2"), default="2", help=schema_help)
    t = sub.add_parser("template")
    t.add_argument("--fixture", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--label-schema", choices=("1", "2"), default="2", help=schema_help)
    s = sub.add_parser("score")
    s.add_argument("--report", required=True, help="release report (scripts/ask/release.py run --out)")
    s.add_argument("--labels", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--manifest", help="default: the report's manifest_file")
    s.add_argument("--fixture", help="default: the manifest's cases_file")
    s.add_argument("--journal", help="default: the report's journal_file, else the report path with .jsonl")
    args = parser.parse_args(argv)
    if args.command == "inventory":
        profile = {"1": V1, "2": V2}[args.label_schema]
        if args.report:
            paths = resolve_paths(args.report, args.manifest, args.fixture, args.journal)
            verify(paths)
            cases, rows = load_cases(paths.fixture), load_rows(paths.journal)
        elif args.fixture:
            cases, rows = load_cases(rel(args.fixture)), None
        else:
            parser.error("inventory needs --fixture or --report")
        plans = {cid: plan(case, profile) for cid, case in cases.items()}
        print(json.dumps(inventory(plans, rows), indent=1))
    elif args.command == "template":
        profile = {"1": V1, "2": V2}[args.label_schema]
        fixture = rel(args.fixture)
        write_exclusive(Path(args.out), template(load_cases(fixture), fixture, digest(ROOT / fixture), profile))
    else:
        out = Path(args.out)
        if out.exists():
            raise FileExistsError(f"{out} exists; refusing to overwrite a tier gate report")
        paths = resolve_paths(args.report, args.manifest, args.fixture, args.journal)
        doc = score(Path(args.labels), paths)
        write_exclusive(out, doc)
        print(json.dumps({"out": str(out), "gates": {name: t["gate"] for name, t in doc["tiers"].items()
                                                     if "gate" in t}}, indent=1))


if __name__ == "__main__":
    main()

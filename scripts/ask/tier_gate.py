#!/usr/bin/env python3
"""Offline ADR 0009 tier gate for the second unseen Ask evaluation (nba-scores-kzc.3).

Scores the Jev tier's preserved per-field readings from the frozen journal against
field-level gold. It makes no provider calls and never reruns the evaluation.

Gold comes from two sources:

* Mechanical: derived from the frozen fixture labels without judgment. Accept labels
  pin every field their intent reads, except `player` in non-player boxscore scopes
  (the request ignores it). Unsupported labels whose reason only an interpreter can
  produce pin the intent.
* Labeled: everything else, from an isolated labeler's file (see
  docs/verification/ask-unseen-two-2026-09-29-field-label-brief.md).

Commands:

* `inventory`: count gold fields by source, field and family. No labels, no scores.
* `template --out PATH`: write the labeling template from the fixture alone.
* `score --labels PATH --out PATH`: verify frozen hashes, score, write the report.

Field definition, acceptance and correctness rules are in `RULES` below and in the
report. Outputs are created exclusively; existing files are never overwritten.
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
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.ask.eval.runner import LabeledCase  # noqa: E402
from server.ask.models.candidates import CandidateLookupResult  # noqa: E402
from server.ask.models.common import DateComponents, Stat  # noqa: E402
from server.ask.models.interpreter import UnsupportedReason  # noqa: E402
from server.ask.normalize import RELEVANT_FIELDS, reference_date, resolve_components  # noqa: E402

FIXTURE = "server/tests/ask/fixtures/eval/unseen-two-2026-09-29.json"
MANIFEST = "docs/verification/ask-unseen-two-2026-09-29-manifest.json"
JOURNAL = "docs/verification/ask-unseen-two-2026-09-29.jsonl"
REPORT = "docs/verification/ask-unseen-two-2026-09-29.json"
PLAYER_CATALOG = "server/ask/data/player_catalog.json"
FRANCHISES = "server/ask/data/franchise_history.json"
# The manifest and strict report pin the fixture and manifest. Neither records the
# journal or report hash, so those two are pinned to commit 377001f, which added them.
PINNED_SHA256 = {
    FIXTURE: "fa3e001b816baf38967fd88c837b6228f2336af811749f06499cd4b59c1cf040",
    MANIFEST: "f188b8440715a4d0f15c58c92cf647dd815bf37db362febace1a29bebb47ca4e",
    JOURNAL: "c43d1b9c99e3fbb917d9808a27873365c38dae83b2ed08a3ab53d513b6059fd4",
    REPORT: "30e142e3f4f81c8348008fa8e9ab58de9f09a9a4fa8e45e12c68f1b649c27a01",
}
LABEL_SCHEMA = "ask-tier-gate-field-labels/1"

TIER = "jev"
TIER_MODEL = "jev-1.13.0"
ACCEPT_MIN = 0.85
PRECISION_MIN = 0.98
COVERAGE_MIN = 0.30
# Scorer choice, not ADR text: a pass is provisional when one more accepted-field
# error would fail precision, or coverage is below this.
PROVISIONAL_COVERAGE = 0.35

FAMILIES = ("game_search", "boxscore_stat", "playoff_series", "postseason_summary")
INTENTS = FAMILIES
FIELDS = ("intent", "stat_scope", "stat", "aggregation", "player", "teams", "date", "season", "round",
          "game_number", "location")
CLOSED = {"intent", "stat_scope", "stat", "aggregation"}
CANDIDATE_SET = {"player": "player", "teams": "team", "date": "date", "season": "season", "round": "round",
                 "game_number": "game_number", "location": "location"}
STAT_SCOPES = {"player", "team", "leaders"}
AGGREGATIONS = {"total", "per_game"}
ROUNDS = {"first_round", "conference_semifinals", "conference_finals", "finals"}
CONFERENCES = {"east", "west", None}
UNSUPPORTED_REASONS = set(UnsupportedReason.__args__)
# Only the normalizer produces these; an interpreter may read the question as a
# supported intent with an unsupported parameter, so the intent needs a label.
NORMALIZER_UNSUPPORTED = {"multi_game_average", "unsupported_leader_stat"}
STATUSES = {"value", "absent", "ambiguous", "unresolved", "unlisted"}
UNLISTED_FIELDS = {"player", "teams", "location"}

RULES = [
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


@dataclass
class CasePlan:
    case_id: str
    family: str
    label_scope: str | None  # None (fully mechanical), "all", or "player"
    scored_intent: str | None = None  # an intent or "unsupported"; None until labeled
    gold: dict[str, list[Gold]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)  # field -> mechanical | labeled
    notes: dict[str, str] = field(default_factory=dict)


def family_of(case_id: str) -> str:
    for family in FAMILIES:
        if f"-{family}-" in case_id:
            return family
    raise IntegrityError(f"{case_id}: no family in id")


def _round(round_name: str | None, conference: str | None) -> Gold:
    return Gold("value", (round_name, conference)) if round_name else ABSENT


def request_gold(request: Any) -> tuple[dict[str, Gold], list[str]]:
    """Mechanical gold for an accept label, plus fields the request leaves undetermined."""
    gold: dict[str, Gold] = {"intent": Gold("value", request.intent)}
    undetermined: list[str] = []

    def teams(refs) -> Gold:
        return Gold("value", frozenset(t.team_id for t in refs)) if refs else ABSENT

    if request.intent == "game_search":
        gold["date"] = Gold("value", (request.dates.start, request.dates.end))
        gold["teams"] = teams(request.teams)
        gold["location"] = Gold("value", city_key(request.location.city)) if request.location else ABSENT
    elif request.intent == "boxscore_stat":
        game = request.game
        gold["stat_scope"] = Gold("value", request.scope)
        gold["stat"] = Gold("value", request.stat.stat)
        gold["aggregation"] = Gold("value", request.stat.aggregation)
        if request.scope == "player":
            gold["player"] = Gold("value", request.player.player_id)
        else:
            undetermined.append("player")
        gold["teams"] = teams(game.teams)
        gold["date"] = Gold("value", (game.date, game.date)) if game.date else ABSENT
        gold["season"] = Gold("value", game.season) if game.season else ABSENT
        gold["round"] = _round(game.round, game.conference)
        gold["game_number"] = Gold("value", game.game_number) if game.game_number else ABSENT
    elif request.intent == "playoff_series":
        gold["season"] = Gold("value", request.season)
        gold["teams"] = teams(request.teams)
        gold["round"] = _round(request.round, request.conference)
    else:
        gold["season"] = Gold("value", request.season)
        gold["teams"] = Gold("value", frozenset({request.team.team_id})) if request.team else ABSENT
    return gold, undetermined


def plan(case: LabeledCase) -> CasePlan:
    family = family_of(case.id)
    if case.action == "accept":
        gold, undetermined = request_gold(case.request)
        p = CasePlan(case.id, family, "player" if undetermined else None, case.request.intent,
                     {k: [v] for k, v in gold.items()}, {k: "mechanical" for k in gold})
        return p
    if case.action == "unsupported" and case.unsupported_reason not in NORMALIZER_UNSUPPORTED:
        return CasePlan(case.id, family, None, "unsupported",
                        {"intent": [Gold("value", f"unsupported:{case.unsupported_reason}")]},
                        {"intent": "mechanical"})
    return CasePlan(case.id, family, "all")


def fields_for(intent: str) -> list[str]:
    if intent == "unsupported":
        return ["intent"]
    return [f for f in FIELDS if f == "intent" or f in RELEVANT_FIELDS[intent]]


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
    if field_name == "player":
        return raw if isinstance(raw, int) and raw in ref.players else fail("player_id not in player_catalog.json")
    if field_name == "teams":
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


def parse_intent(raw: Any, where: str) -> str:
    if raw in INTENTS:
        return raw
    if isinstance(raw, str) and raw.startswith("unsupported:") and raw.split(":", 1)[1] in UNSUPPORTED_REASONS:
        return raw
    raise ValueError(f"{where}: intent must be an intent or unsupported:<reason>: {raw!r}")


def parse_one(field_name: str, raw: Any, ref: Reference, where: str) -> Gold:
    if not isinstance(raw, dict) or raw.get("status") not in STATUSES:
        raise ValueError(f"{where}: status must be one of {sorted(STATUSES)}")
    status = raw["status"]
    extra = set(raw) - {"status", "value", "alternatives", "reason", "note"}
    if extra:
        raise ValueError(f"{where}: unknown keys {sorted(extra)}")
    if field_name == "intent":
        if status != "value":
            raise ValueError(f"{where}: intent labels are values")
        return Gold("value", parse_intent(raw.get("value"), where))
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


def parse_field(field_name: str, raw: Any, ref: Reference, where: str) -> tuple[list[Gold], str | None]:
    if isinstance(raw, dict) and "any_of" in raw:
        options, note = raw["any_of"], raw.get("note")
        if set(raw) - {"any_of", "note"} or not isinstance(options, list) or len(options) < 2:
            raise ValueError(f"{where}: any_of needs two or more labels")
        if not (isinstance(note, str) and note.strip()):
            raise ValueError(f"{where}: any_of needs a note")
        return [parse_one(field_name, o, ref, f"{where}[{i}]") for i, o in enumerate(options)], note
    if raw is None:
        raise ValueError(f"{where}: not labeled")
    return [parse_one(field_name, raw, ref, where)], None


def apply_labels(plans: dict[str, CasePlan], labels: dict[str, Any], ref: Reference) -> None:
    """Validate the labeler's file and merge it into the plans."""
    if labels.get("schema") != LABEL_SCHEMA:
        raise ValueError(f"labels schema must be {LABEL_SCHEMA}")
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
            intent_options, note = parse_field("intent", row.get("intent"), ref, f"{cid}.intent")
            scored = row.get("scored_intent")
            values = {g.value for g in intent_options}
            supported = {v for v in values if v in INTENTS}
            if scored not in (*INTENTS, "unsupported"):
                raise ValueError(f"{cid}: scored_intent must be an intent or 'unsupported'")
            if scored == "unsupported" and supported:
                raise ValueError(f"{cid}: a supported intent is acceptable; score its fields")
            if scored != "unsupported" and scored not in values:
                raise ValueError(f"{cid}: scored_intent must be one of the acceptable intents")
            expected = set(fields_for(scored)) - {"intent"}
            if set(fields) != expected:
                raise ValueError(f"{cid}: {scored} needs exactly fields {sorted(expected)}, got {sorted(fields)}")
            p.scored_intent = scored
            p.gold["intent"] = intent_options
            p.sources["intent"] = "labeled"
            if note:
                p.notes["intent"] = note
        for name, raw in fields.items():
            options, note = parse_field(name, raw, ref, f"{cid}.{name}")
            p.gold[name] = options
            p.sources[name] = "labeled"
            if note:
                p.notes[name] = note


def label_warnings(cases: dict[str, LabeledCase], plans: dict[str, CasePlan]) -> list[str]:
    """Labels that disagree with the frozen clarification or unsupported label. Uses no traces."""
    warnings = []
    for cid, p in plans.items():
        case = cases[cid]
        if case.action == "clarify" and case.clarify_field in p.gold:
            statuses = {g.status for g in p.gold[case.clarify_field]}
            want = {"missing": {"absent"}, "ambiguous": {"ambiguous"}, "year_required": {"unresolved"},
                    "range_too_long": {"unresolved"}, "no_matching_candidate": {"unlisted"}}.get(case.clarify_reason)
            if want and not statuses & want:
                warnings.append(f"{cid}: clarify {case.clarify_field}/{case.clarify_reason} labeled "
                                f"{sorted(statuses)}")
        elif case.action == "clarify" and p.scored_intent and case.clarify_field not in p.gold:
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


def _default(field_name: str, kind: str, payload: Any, scope_is_leaders: bool) -> tuple[str, Any]:
    if kind == "absent" and field_name == "aggregation":
        return "value", "total"
    if kind == "absent" and field_name == "stat" and not scope_is_leaders:
        return "value", "stat_line"
    return kind, payload


def _gold_default(field_name: str, gold: Gold, scope_is_leaders: bool) -> Gold:
    kind, payload = _default(field_name, gold.status, gold.value, scope_is_leaders)
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
          scope_is_leaders: bool) -> tuple[bool, str | None]:
    kind, payload = _default(field_name, kind, payload, scope_is_leaders)
    golds = [_gold_default(field_name, g, scope_is_leaders) for g in golds]
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


def _tier_record(row: dict[str, Any], tier: str) -> dict[str, Any] | None:
    records = [r for r in row["tier_outputs"] if r["tier"] == tier]
    if len(records) > 1:
        raise IntegrityError(f"{row['case_id']}: {len(records)} {tier} outputs; expected one attempt")
    return records[0]["output"] if records else None


def _scope_is_leaders(p: CasePlan) -> bool:
    return any(g.status == "value" and g.value == "leaders" for g in p.gold.get("stat_scope", []))


def _extracted(output: dict[str, Any], cands: CandidateLookupResult, case: LabeledCase) -> tuple[str, Any] | None:
    raw = output.get("extracted_date")
    if raw is None or cands.sets["date"].status == "candidates":
        return None
    resolved = resolve_components(DateComponents.model_validate(raw), reference_date(case.context))
    if isinstance(resolved, str):
        return ("unresolved", resolved) if resolved != "invalid_date" else ("absent", None)
    return "value", (resolved.start, resolved.end)


def score_tier(tier: str, accept_min: float | None, cases: dict[str, LabeledCase], plans: dict[str, CasePlan],
               rows: dict[str, dict[str, Any]], *, only: set[tuple[str, str]] | None = None) -> list[Scored]:
    """Score one tier's readings. `accept_min=None` marks a final tier (every reading is final).
    `only` restricts scoring to (case_id, field) pairs, e.g. fields an earlier tier escalated."""
    out: list[Scored] = []
    for cid, p in plans.items():
        row = rows[cid]
        cands = CandidateLookupResult.model_validate(row["candidates"])
        output = _tier_record(row, tier)
        later = [r["tier"] for r in row["tier_outputs"]]
        escalates = tier in later and later.index(tier) < len(later) - 1
        for name in fields_for(p.scored_intent):
            if name == "location" and cands.sets["location"].status == "not_mentioned":
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
                item.correct, item.error_kind = judge(name, kind, payload, p.gold[name], cands, _scope_is_leaders(p))
            item.disposition = "accepted" if accepted else ("escalated" if escalates else "not_escalated")
    return out


def check_cascade(tier: str, accept_min: float, rows: dict[str, dict[str, Any]], scored: list[Scored]) -> None:
    """The acceptance rule must agree with which tier the frozen cascade credited."""
    by_key = {(s.case_id, s.field): s for s in scored}
    for cid, row in rows.items():
        output = _tier_record(row, tier)
        final = row["attempts"][-1]["output"]["metadata"]["field_tiers"] if row["attempts"] else {}
        for name, decided_by in final.items():
            if decided_by == "lookup":
                if row["candidates"]["sets"][name]["status"] != "not_mentioned":
                    raise IntegrityError(f"{cid}:{name} lookup-decided with candidates")
                continue
            if output is None or output["outcome"] == "unavailable":
                if decided_by == tier:
                    raise IntegrityError(f"{cid}:{name} credited to {tier} without an output")
                continue
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
            if decided_by not in (tier, "veto") and accepted and not overridden:
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


def breakdown(items: list[Scored], key: str) -> dict[str, Any]:
    order = FIELDS if key == "field" else FAMILIES
    groups = {k: [s for s in items if getattr(s, key) == k] for k in order}
    return {k: metrics(v) for k, v in groups.items() if v}


def error_rows(items: list[Scored]) -> list[dict[str, Any]]:
    return [{"case_id": s.case_id, "field": s.field, "source": s.source, "reading": s.reading,
             "confidence": s.confidence, "gold": [g.show() for g in s.gold], "error_kind": s.error_kind}
            for s in items if s.disposition == "accepted" and not s.correct]


def inventory(plans: dict[str, CasePlan], rows: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Gold fields by source. Labeled cases' field counts depend on the labeled intent,
    so they are reported as the fields of the family's intent (an estimate)."""
    counts: dict[str, dict[str, dict[str, int]]] = {"mechanical": {}, "labeled": {}, "lookup_decided": {}}

    def add(bucket: str, family: str, name: str) -> None:
        fam = counts[bucket].setdefault(family, {})
        fam[name] = fam.get(name, 0) + 1

    for cid, p in plans.items():
        intent = p.scored_intent or p.family
        location_by_lookup = rows is not None and rows[cid]["candidates"]["sets"]["location"]["status"] == "not_mentioned"
        for name in fields_for(intent):
            if name == "location" and location_by_lookup:
                add("lookup_decided", p.family, name)
            elif p.sources.get(name) == "mechanical":
                add("mechanical", p.family, name)
            else:
                add("labeled", p.family, name)
    totals = {bucket: sum(sum(f.values()) for f in fams.values()) for bucket, fams in counts.items()}
    return {"by_bucket": counts, "totals": totals,
            "labeled_cases": sorted(cid for cid, p in plans.items() if p.label_scope),
            "note": "labeled counts assume each labeled case's family intent; the labeler may choose another"}


# -- loading and verification ------------------------------------------------------------------


def load_cases(root: Path = ROOT) -> dict[str, LabeledCase]:
    raw = json.loads((root / FIXTURE).read_text())["cases"]
    return {c["id"]: LabeledCase.from_json(c) for c in raw}


def load_rows(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    rows = [json.loads(line) for line in (root / JOURNAL).read_text().splitlines() if line.strip()]
    return {row["case_id"]: row for row in rows}


def verify(root: Path = ROOT, pinned: dict[str, str] = PINNED_SHA256) -> dict[str, str]:
    hashes = {path: digest(root / path) for path in pinned}
    changed = [path for path, sha in pinned.items() if hashes[path] != sha]
    if changed:
        raise IntegrityError(f"frozen inputs changed: {changed}")
    manifest = json.loads((root / MANIFEST).read_text())
    report = json.loads((root / REPORT).read_text())
    if manifest["cases_sha256"] != hashes[FIXTURE] or report["cases_sha256"] != hashes[FIXTURE]:
        raise IntegrityError("fixture hash differs from the manifest or report")
    if report["manifest_sha256"] != hashes[MANIFEST]:
        raise IntegrityError("manifest hash differs from the report")
    config = manifest["configuration"]
    if config["jev_model"] != TIER_MODEL or config["jev_accept_min"] != ACCEPT_MIN or config["laya_base_url"]:
        raise IntegrityError("frozen configuration differs from the scored tier")
    cases, rows = load_cases(root), load_rows(root)
    if list(cases) != list(rows) or [c["case_id"] for c in report["cases"]] != list(rows):
        raise IntegrityError("journal, report and fixture cases differ")
    for cid, row in rows.items():
        output = _tier_record(row, TIER)
        if output is None or output["metadata"]["model"] != TIER_MODEL:
            raise IntegrityError(f"{cid}: no {TIER_MODEL} output")
    return hashes


def template(cases: dict[str, LabeledCase]) -> dict[str, Any]:
    """The labeling template. Built from the fixture alone; carries no trace content."""
    items = []
    for cid, case in cases.items():
        p = plan(case)
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
    return {
        "schema": LABEL_SCHEMA,
        "fixture": FIXTURE,
        "fixture_sha256": PINNED_SHA256[FIXTURE],
        "labeler": {"name": "", "labeled_at": "", "isolation_statement": ""},
        "fields_by_intent": {intent: [f for f in fields_for(intent) if f != "intent"]
                             for intent in (*INTENTS, "unsupported")},
        "cases": items,
    }


def score(labels_path: Path, root: Path = ROOT) -> dict[str, Any]:
    hashes = verify(root)
    cases, rows = load_cases(root), load_rows(root)
    labels = json.loads(labels_path.read_text())
    if labels.get("fixture_sha256") != hashes[FIXTURE]:
        raise IntegrityError("labels were made for a different fixture")
    plans = {cid: plan(case) for cid, case in cases.items()}
    apply_labels(plans, labels, Reference.load(root))
    return build_report(cases, plans, rows, hashes | {str(labels_path): digest(labels_path)})


def build_report(cases, plans, rows, hashes) -> dict[str, Any]:
    jev = score_tier(TIER, ACCEPT_MIN, cases, plans, rows)
    check_cascade(TIER, ACCEPT_MIN, rows, jev)
    escalated = {(s.case_id, s.field) for s in jev if s.disposition == "escalated"}
    luna = score_tier("luna", None, cases, plans, rows, only=escalated)
    luna_read = [s for s in luna if s.reading is not None]
    return {
        "purpose": "Offline ADR 0009 tier gate from preserved traces; no provider calls, no rerun",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs_sha256": hashes,
        "tier": {"name": TIER, "model": TIER_MODEL, "accept_min": ACCEPT_MIN},
        "rules": RULES,
        "gold_inventory": inventory(plans, rows),
        "label_notes": {cid: p.notes for cid, p in plans.items() if p.notes},
        "label_warnings": label_warnings(cases, plans),
        "tiers": {
            TIER: {"gate": gate(jev), "by_field": breakdown(jev, "field"), "by_family": breakdown(jev, "family"),
                   "by_gold_source": {src: metrics([s for s in jev if s.source == src])
                                      for src in ("mechanical", "labeled")},
                   "accepted_field_errors": error_rows(jev)},
            "luna": {"informational": "final tier, no confidences; readings on fields Jev escalated",
                     "fields": len(luna), "read": len(luna_read),
                     "correct": sum(1 for s in luna_read if s.correct),
                     "by_field": {k: {"read": len(v), "correct": sum(1 for s in v if s.correct)}
                                  for k in FIELDS if (v := [s for s in luna_read if s.field == k])}},
            "laya": {"informational": "disabled in the frozen configuration; no readings"},
        },
        "scope_limits": [
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
        ],
    }


def write_exclusive(path: Path, doc: dict[str, Any]) -> None:
    with path.open("x") as out:
        out.write(json.dumps(doc, indent=1) + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    t = sub.add_parser("template")
    t.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--labels", required=True)
    s.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "inventory":
        verify()
        plans = {cid: plan(case) for cid, case in load_cases().items()}
        print(json.dumps(inventory(plans, load_rows()), indent=1))
    elif args.command == "template":
        write_exclusive(Path(args.out), template(load_cases()))
    else:
        out = Path(args.out)
        if out.exists():
            raise FileExistsError(f"{out} exists; refusing to overwrite a tier gate report")
        doc = score(Path(args.labels))
        write_exclusive(out, doc)
        print(json.dumps({"out": str(out), "gate": doc["tiers"][TIER]["gate"]}, indent=1))


if __name__ == "__main__":
    main()

"""Short-lived, server-validated continuation state for Ask clarifications."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from server.ask.models.candidates import CandidateLookupResult, DateCandidateValue
from server.ask.models.interpreter import FieldInterpretation, InterpreterOutput
from server.ask.models.request import AskContext
from server.ask.normalize import reference_date, resolve_components


def _digest(value: str) -> str:
    return hashlib.sha256(value.strip().casefold().encode("utf-8")).hexdigest()


def _client_context(context: AskContext) -> str:
    return json.dumps({
        "route": context.route,
        "view_date": context.view_date.isoformat() if context.view_date else None,
        "game_id": context.game_id,
        "playoff_season": context.playoff_season,
    }, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class PendingResolution:
    output: InterpreterOutput
    candidates: CandidateLookupResult
    context: AskContext


class ResolutionStore:
    """Opaque random tokens backed by SQLite, shared across app workers.

    A token authorizes only the exact rewritten option question and app context
    for which it was issued. The stored interpretation is validated again by
    the normalizer before any basketball resolver executes.
    """

    def __init__(self, path: str | os.PathLike[str] | None = None, ttl_seconds: int = 900):
        state_dir = Path(os.getenv("ASK_STATE_DIR", ".ask-state"))
        self.path = Path(path) if path is not None else state_dir / "resolution.sqlite3"
        self.ttl_seconds = ttl_seconds

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("CREATE TABLE IF NOT EXISTS resolution_tokens ("
                           "token TEXT PRIMARY KEY, question_hash TEXT NOT NULL, client_hash TEXT NOT NULL, "
                           "expires REAL NOT NULL, payload TEXT NOT NULL)")
        return connection

    def issue(self, question: str, pending: PendingResolution) -> str:
        token = secrets.token_urlsafe(24)
        payload = json.dumps({
            "output": pending.output.model_dump(mode="json"),
            "candidates": pending.candidates.model_dump(mode="json"),
            "context": pending.context.model_dump(mode="json"),
        }, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute("DELETE FROM resolution_tokens WHERE expires < ?", (time.time(),))
            connection.execute("INSERT INTO resolution_tokens VALUES (?, ?, ?, ?, ?)",
                               (token, _digest(question), _digest(_client_context(pending.context)),
                                time.time() + self.ttl_seconds, payload))
        return token

    def read(self, token: str, question: str, context: AskContext) -> PendingResolution | None:
        if not token or len(token) > 512:
            return None
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT question_hash, client_hash, expires, payload FROM resolution_tokens WHERE token = ?", (token,)
                ).fetchone()
            if row is None or row[2] < time.time():
                return None
            if row[0] != _digest(question) or row[1] != _digest(_client_context(context)):
                return None
            data = json.loads(row[3])
            return PendingResolution(
                output=InterpreterOutput.model_validate(data["output"]),
                candidates=CandidateLookupResult.model_validate(data["candidates"]),
                context=AskContext.model_validate(data["context"]),
            )
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
            return None


def choose(pending: PendingResolution, field: str, candidate_id: str | None = None, year: int | None = None) -> PendingResolution:
    """Apply only a server-offered choice to a validated pending interpretation."""
    output, candidates = pending.output, pending.candidates
    if year is not None:
        if field != "date" or not 1946 <= year <= 2100:
            raise ValueError("Invalid year choice")
        date_field = output.get_field("date")
        if date_field and date_field.status == "selected":
            selected_id = date_field.selected[0]
            date_set = candidates.sets["date"]
            amended = []
            for candidate in date_set.candidates:
                if candidate.id != selected_id:
                    amended.append(candidate)
                    continue
                if candidate.value.kind != "date" or candidate.value.components.year is not None:
                    raise ValueError("Date does not need a year")
                parts = candidate.value.components.model_copy(update={"year": year})
                resolved = resolve_components(parts, reference_date(pending.context))
                value = DateCandidateValue(components=parts, resolved=resolved if not isinstance(resolved, str) else None,
                                           unresolved_reason=resolved if isinstance(resolved, str) else None)
                amended.append(candidate.model_copy(update={"value": value}))
            candidates = candidates.model_copy(update={"sets": {**candidates.sets,
                "date": date_set.model_copy(update={"candidates": amended})}})
        elif output.extracted_date and output.extracted_date.year is None:
            output = output.model_copy(update={"extracted_date": output.extracted_date.model_copy(update={"year": year})})
        else:
            raise ValueError("Date does not need a year")
    elif candidate_id is not None:
        candidate_field = "team" if field == "teams" else field
        candidate = candidates.by_id(candidate_id)
        if candidate is None or candidate.field != candidate_field:
            raise ValueError("Unknown clarification choice")
        replacement = FieldInterpretation(field=field, status="selected", selected=[candidate_id], confidence=1)
        output = output.model_copy(update={"fields": [f for f in output.fields if f.field != field] + [replacement]})
    else:
        raise ValueError("No clarification choice")
    return PendingResolution(output=output, candidates=candidates, context=pending.context)

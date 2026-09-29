"""Playoff series results, numbered playoff games and postseason summaries.

Everything reads the cached playoffs payload the bracket and series pages use
(``playoffs.get_playoff_games_and_series``), so rounds, winners and series
slugs match the app. Postseason membership comes from those dated game
records, never from current rosters.

Historical formats map onto the contract's modern round names by distance from
the championship round: the last round is ``finals``, the one before it
``conference_finals``, then ``conference_semifinals``, then ``first_round``
(so the 1947-48 "Semifinals" are ``conference_finals``, and the 1950 "NBA
Semifinals" are ``conference_finals`` with its Division Finals one round
earlier).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import logging
from typing import Sequence

from server.ask import links
from server.ask.models.common import Conference, PlayoffRound, TeamRef
from server.ask.models.response import (
    GameResultItem,
    PlayoffSeriesResult,
    PostseasonRoundRow,
    PostseasonSeriesRow,
    PostseasonSummaryResult,
    ScoreboardGame,
    SeriesTeamRow,
    SeriesParticipant,
    WinLoss,
)
from server.ask.resolvers import data
from server.ask.resolvers.errors import AmbiguousError, NotFoundError
from server.ask.resolvers.games import ResolvedGame, get_scoreboard_game, int_or_none, team_ref, validate_team_ids
from server.ask.resolvers.output import ResolverOutput, stats_source
from server.ask.spoilers import game_spoilers, guard, open_value
from server.services import playoffs as playoffs_service

logger = logging.getLogger(__name__)

FIRST_PLAYOFF_YEAR = 1947
_ROUNDS_FROM_FINALS: dict[int, PlayoffRound] = {
    0: "finals",
    1: "conference_finals",
    2: "conference_semifinals",
    3: "first_round",
}


def _check_season(season: str) -> None:
    if links.season_to_year(season) < FIRST_PLAYOFF_YEAR:
        raise NotFoundError("no_record", "before_records", "No playoffs were played before 1947")


def contract_round(season: str, series: dict) -> PlayoffRound | None:
    if series.get("isFinals"):
        return "finals"
    names = playoffs_service.get_round_names(season)
    round_number = int_or_none(series.get("round"))
    if round_number not in names:
        return None
    return _ROUNDS_FROM_FINALS.get(max(names) - round_number)


def conference(series: dict) -> Conference | None:
    group = str(series.get("bracketGroupId") or "")
    if series.get("isFinals"):
        return None
    return "east" if group.startswith("east") else "west" if group.startswith("west") else None


def _payload(season: str) -> dict:
    _check_season(season)
    payload = data.playoffs(season)
    if not payload.get("series"):
        raise NotFoundError("no_record", "no_postseason_records", details={"season": season})
    return payload


def _is_past_season(season: str) -> bool:
    return int(season[:4]) < int(playoffs_service.get_current_season()[:4])


def _team_ids(series: dict) -> list[int]:
    return [int(team["id"]) for team in series.get("teams") or []]


def _wins(series: dict) -> dict[int, int]:
    return {int(team_id): int(count) for team_id, count in (series.get("wins") or {}).items()}


def _winner(season: str, series: dict) -> int | None:
    """The series winner once decided, else None."""
    wins = _wins(series)
    if not wins:
        return None
    leader, most = max(wins.items(), key=lambda item: item[1])
    target = int_or_none(series.get("targetWins"))
    if target is not None and most >= target:
        return leader
    # Past postseasons are over even where a format had no fixed target
    # (the 1954 round robin); a tie still names no winner.
    others = [count for team_id, count in wins.items() if team_id != leader]
    if target is None and _is_past_season(season) and len(wins) >= 2 and all(count < most for count in others):
        return leader
    return None


def _series_games(series: dict) -> list[dict]:
    return sorted(series.get("games") or [], key=lambda game: (str(game.get("date")), str(game.get("gameId"))))


def _game_item(game: dict) -> GameResultItem:
    """A GameResultItem for a completed playoff game from the playoffs payload.

    The game log has no scoreboard payload, so this one is built from it:
    status "Final", no period, labels or series text; ``teamName`` holds the
    full name the log reports.
    """
    day = dt.date.fromisoformat(str(game["date"])[:10])

    def side(team):
        return {"teamId": int(team["id"]), "teamName": team.get("name") or team["tricode"],
                "teamTricode": team["tricode"], "score": int(team["score"])}

    payload = ScoreboardGame(
        gameId=str(game["gameId"]),
        gameStatus=3,
        gameStatusText="Final",
        boxscoreAvailable=bool(game.get("boxscoreAvailable")),
        homeTeam=side(game["homeTeam"]),
        awayTeam=side(game["awayTeam"]),
    )
    item_links = [links.boxscore_link(payload.gameId, day)] if payload.boxscoreAvailable else []
    return GameResultItem(date=day, game=payload, spoilers=game_spoilers(3), links=item_links)


def _select_series(
    season: str,
    payload: dict,
    team_ids: Sequence[int],
    round_: PlayoffRound | None,
    conference_: Conference | None,
) -> dict:
    ids = validate_team_ids(team_ids)
    if not ids and round_ is None:
        raise ValueError("A team or a round is required to choose a series")
    matches = [
        series for series in payload["series"]
        if set(ids) <= set(_team_ids(series))
        and (round_ is None or contract_round(season, series) == round_)
        and (conference_ is None or conference(series) == conference_)
    ]
    if not matches:
        # For a named team, "no such series" reveals an earlier elimination.
        raise NotFoundError(
            "no_record", "no_matching_series", spoiler=bool(ids),
            details={"season": season, "teamIds": list(ids), "round": round_, "conference": conference_},
        )
    if len(matches) > 1:
        # Candidates reveal who reached the round, so they are protected.
        raise AmbiguousError(
            "round" if len(ids) == 2 else "teams",
            "several_series",
            spoiler=True,
            options=[
                {"series_key": series.get("seriesKey"), "round": contract_round(season, series),
                 "conference": conference(series), "teams": [team_ref(team) for team in series.get("teams") or []]}
                for series in matches
            ],
        )
    return matches[0]


def _summary(series: dict, winner: int | None, refs: dict[int, TeamRef]) -> str:
    wins = _wins(series)
    ordered = sorted(wins.items(), key=lambda item: -item[1])
    if not ordered:
        return "Series not started"
    (lead_id, lead), *rest = ordered
    trail = rest[0][1] if rest else 0
    code = refs[lead_id].tricode if lead_id in refs else "Team"
    if winner is not None:
        return f"{code} won {lead}-{trail}"
    return f"Series tied {lead}-{trail}" if lead == trail else f"{code} leads {lead}-{trail}"


def series_result(
    season: str,
    team_ids: Sequence[int] = (),
    round_: PlayoffRound | None = None,
    conference_: Conference | None = None,
) -> ResolverOutput[PlayoffSeriesResult]:
    """One series, chosen by season plus two teams, a team and round, the
    finals, or a conference and round. Teams the caller did not name are
    protected because they reveal advancement."""
    payload = _payload(season)
    series = _select_series(season, payload, team_ids, round_, conference_)
    mapped_round = contract_round(season, series)
    if mapped_round is None:
        raise NotFoundError("no_record", "round_not_determined", details={"seriesKey": series.get("seriesKey")})
    refs = {ref.team_id: ref for ref in (team_ref(team) for team in series.get("teams") or []) if ref}
    named = list(dict.fromkeys(team_ids))
    order = named + [team_id for team_id in refs if team_id not in named]
    winner = _winner(season, series)
    wins = _wins(series)
    games = _series_games(series)
    rows = [
        SeriesTeamRow(
            team=guard(refs[team_id], spoiler=team_id not in named),
            seed=open_value(None),  # the playoffs payload carries no seeds
            wins=guard(wins.get(team_id, 0)),
            won_series=guard(None if winner is None else winner == team_id),
        )
        for team_id in order
    ]
    status = "complete" if winner is not None else "in_progress" if games else "not_started"
    result = PlayoffSeriesResult(
        season=season,
        round=mapped_round,
        conference=conference(series),
        teams=rows,
        status=guard(status),
        games_played=guard(len(games)),
        summary=guard(_summary(series, winner, refs)),
        games=guard([_game_item(game) for game in games]),
    )
    link = links.series_link(season, series)
    if link is not None and not set(refs) <= set(named):
        link = link.model_copy(update={"spoiler": True})
    return ResolverOutput(
        result,
        tuple(filter(None, (link, links.bracket_link(season)))),
        (stats_source(winner is not None),),
    )


def find_playoff_game(
    season: str,
    game_number: int,
    team_ids: Sequence[int] = (),
    round_: PlayoffRound | None = None,
    conference_: Conference | None = None,
) -> ResolvedGame:
    """Game ``game_number`` of one series, verified on its date's scoreboard.

    A game the series never reached is ``no_record`` with ``spoiler=True``.
    """
    if isinstance(game_number, bool) or not isinstance(game_number, int) or not 1 <= game_number <= 7:
        raise ValueError("Game number must be 1-7")
    payload = _payload(season)
    series = _select_series(season, payload, team_ids, round_, conference_)
    games = _series_games(series)
    if game_number > len(games):
        raise NotFoundError(
            "no_record", "series_game_not_played", spoiler=True,
            details={"season": season, "seriesKey": series.get("seriesKey"), "gameNumber": game_number},
        )
    chosen = games[game_number - 1]
    game = get_scoreboard_game(str(chosen["gameId"]), dt.date.fromisoformat(str(chosen["date"])[:10]))
    inferred = not set(_team_ids(series)) <= set(team_ids)
    return dataclasses.replace(
        game, round=contract_round(season, series), game_number=game_number, participants_inferred=inferred, named_team_ids=tuple(team_ids)
    )


def league_postseason(season: str) -> ResolverOutput[PostseasonSummaryResult]:
    """The whole postseason: champion, runner-up and every series."""
    payload = _payload(season)
    rows = []
    champion = runner_up = None
    all_decided = True
    for series in payload["series"]:
        mapped = contract_round(season, series)
        if mapped is None:
            logger.info("Skipping series %s with no determined round", series.get("seriesKey"))
            all_decided = False
            continue
        refs = [ref for ref in (team_ref(team) for team in series.get("teams") or []) if ref]
        wins = _wins(series)
        winner_id = _winner(season, series)
        all_decided = all_decided and winner_id is not None
        winner = next((ref for ref in refs if ref.team_id == winner_id), None)
        loser = next((ref for ref in refs if winner and ref.team_id != winner.team_id), None)
        rows.append(PostseasonSeriesRow(
            round=mapped,
            conference=conference(series),
            teams=[SeriesParticipant(team=ref, wins=wins.get(ref.team_id, 0)) for ref in refs],
            status="complete" if winner_id is not None else "in_progress" if _series_games(series) else "not_started",
            winner_team_id=winner_id,
        ))
        if mapped == "finals" and winner:
            champion, runner_up = winner, loser
    result = PostseasonSummaryResult(
        season=season,
        team=None,
        finish=open_value(None),
        record=open_value(None),
        series_won=open_value(None),
        rounds=open_value([]),
        champion=guard(champion),
        runner_up=guard(runner_up),
        series=guard(rows),
    )
    complete = champion is not None and all_decided
    return ResolverOutput(result, (links.bracket_link(season),), (stats_source(complete),))


def team_postseason(season: str, team: TeamRef) -> ResolverOutput[PostseasonSummaryResult]:
    """One team's postseason. A team with no playoff games finishes
    ``did_not_qualify`` (play-in games are not in the playoffs payload, so a
    play-in loser also reads as ``did_not_qualify``)."""
    payload = _payload(season)
    team_series = sorted(
        (series for series in payload["series"] if team.team_id in _team_ids(series)),
        key=lambda series: (int_or_none(series.get("round")) or 0, playoffs_service.get_series_dates(series)[0]),
    )
    recorded = next(
        (ref for series in team_series for ref in (team_ref(t) for t in series.get("teams") or []) if ref and ref.team_id == team.team_id),
        None,
    )
    rounds: list[PostseasonRoundRow] = []
    wins = losses = series_won = 0
    finish = "did_not_qualify" if not team_series else None
    for series in team_series:
        mapped = contract_round(season, series)
        opponent = next((team_ref(t) for t in series.get("teams") or [] if int(t["id"]) != team.team_id), None)
        if mapped is None or opponent is None:
            logger.info("Skipping series %s with no round or opponent", series.get("seriesKey"))
            continue
        counts = _wins(series)
        winner_id = _winner(season, series)
        won = None if winner_id is None else winner_id == team.team_id
        series_won += bool(won)
        for game in series.get("games") or []:
            if int_or_none(game.get("winnerTeamId")) == team.team_id:
                wins += 1
            elif game.get("winnerTeamId") is not None:
                losses += 1
        rounds.append(PostseasonRoundRow(
            round=mapped,
            conference=conference(series),
            opponent=opponent,
            team_wins=counts.get(team.team_id, 0),
            opponent_wins=counts.get(opponent.team_id, 0),
            won=won,
            series_link=links.series_link(season, series),
        ))
        if won is False:
            finish = f"lost_{mapped}"
        elif won and mapped == "finals":
            finish = "champion"
    if finish is None:
        finish = None if _is_past_season(season) else "in_progress"
    result = PostseasonSummaryResult(
        season=season,
        team=recorded or team,
        # Team scope is protected throughout: even "did not qualify" and an
        # empty rounds list reveal how the season ended.
        finish=guard(finish),
        record=guard(WinLoss(wins=wins, losses=losses) if team_series else None),
        series_won=guard(series_won if team_series else None),
        rounds=guard(rounds),
        champion=open_value(None),
        runner_up=open_value(None),
        series=open_value([]),
    )
    complete = finish not in (None, "in_progress")
    return ResolverOutput(result, (links.bracket_link(season),), (stats_source(complete),))

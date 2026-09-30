import datetime as dt

from server.ask.eval import trace as tr
from server.ask.eval.runner import LabeledCase
from server.ask.interpreters.pricing import SpendGuard
from server.ask.models.request import GameSearchRequest
from server.tests.ask.test_tiered import BOS, CANDIDATES, CLE, CONTEXT, Fake, sel


def case(case_id="c1", teams=(CLE,)):
    request = GameSearchRequest(dates={"start": dt.date(2026, 9, 21), "end": dt.date(2026, 9, 27)},
                                teams=[{"team_id": t.value.team.team_id, "tricode": t.value.team.tricode,
                                        "name": t.value.team.name} for t in teams])
    return LabeledCase(id=case_id, question="cavs games last week", context=CONTEXT, action="accept",
                       request=request)


def collected(jev, luna):
    return tr.collect([case()], lambda _: CANDIDATES, {"jev": jev, "luna": luna}, SpendGuard(1.0))


def test_collect_runs_every_tier_once_and_replay_reproduces():
    jev = Fake("jev", sel("intent", "game_search"), sel("date", "date:0"), sel("teams", CLE.id, confidence=0.7),
               cost=0.0001)
    luna = Fake("luna", sel("intent", "game_search", confidence=None), sel("date", "date:0", confidence=None),
                sel("teams", CLE.id, confidence=None), cost=0.0002)
    trace = collected(jev, luna)
    assert (jev.calls, luna.calls) == (1, 1)
    assert trace["spend"]["spent_usd"] == 0.0003

    # Jev at 0.9 escalates teams to Luna; at 0.6 it answers alone. Neither calls a provider.
    for jev_min, finisher in ((0.9, "luna"), (0.6, "jev")):
        run, summary = tr.evaluate([case()], trace, {"jev": jev_min, "luna": None})
        assert summary["correct"] == 1 and summary["replay_misses"] == 0
        assert summary["tier_share"] == {finisher: 1}
    assert (jev.calls, luna.calls) == (1, 1)


def test_field_oracle_scores_selected_and_absent_reads():
    jev = Fake("jev", sel("intent", "game_search"), sel("date", "date:0", confidence=0.99),
               sel("teams", BOS.id, confidence=0.8))
    trace = collected(jev, Fake("luna"))
    reads = {r.field: r for r in tr.field_reads([case()], trace, "jev")}
    assert reads["intent"].correct and reads["date"].correct
    assert not reads["teams"].correct
    stats = tr.tier_stats(list(reads.values()), 0.9)
    assert (stats["accepted"], stats["precision"]) == (2, 1.0)
    chosen = tr.calibrate_tier(list(reads.values()), grid=(0.7, 0.8, 0.9))["chosen"]
    assert chosen["threshold"] == 0.9  # 0.8 would accept the wrong team


def test_calibration_never_picks_a_dip_below_a_failing_threshold():
    reads = [tr.FieldRead("a", "date", 0.95, False), tr.FieldRead("b", "date", 0.85, True),
             tr.FieldRead("c", "date", 0.99, True)]
    # 0.8 has precision 2/3, 0.9 has 1/2, 0.96 has 1/1: only 0.96 and above are safe.
    chosen = tr.calibrate_tier(reads, precision_min=0.98, grid=(0.8, 0.9, 0.96))["chosen"]
    assert chosen["threshold"] == 0.96


def test_stage2_absent_defaults_score_as_executed_request():
    from server.ask.candidates.lookup import CandidateLookupService
    from server.ask.models.request import TeamRecordsRequest
    from server.tests.ask.test_tiered import absent
    q='2023-24 NBA standings';cands=CandidateLookupService().lookup(q,CONTEXT)
    label=LabeledCase(id='defaults',question=q,context=CONTEXT,action='accept',request=TeamRecordsRequest(season='2023-24'))
    jev=Fake('jev',sel('intent','team_records'),sel('season','season:2023-24'),absent('teams'),absent('season_type'),absent('standings_scope'))
    trace=tr.collect([label],lambda _:cands,{'jev':jev},SpendGuard(1))
    reads={r.field:r for r in tr.field_reads([label],trace,'jev')}
    assert reads['season_type'].correct and reads['standings_scope'].correct
    east=LabeledCase(id='defaults',question=q,context=CONTEXT,action='accept',request=TeamRecordsRequest(season='2023-24',standings_scope='east'))
    assert not next(r for r in tr.field_reads([east],trace,'jev') if r.field=='standings_scope').correct

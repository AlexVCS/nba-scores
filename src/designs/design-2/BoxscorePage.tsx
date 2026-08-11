import {Fragment, useState} from "react";
import {Link} from "react-router";
import {ChevronDown, ChevronLeft, ExternalLink} from "lucide-react";
import PlayerHeadshot from "@/components/PlayerHeadshot";
import type {Player} from "@/helpers/helpers";
import {formatMinutesPlayed, formatPlayerNameLink} from "@/helpers/helpers";
import {useBoxscorePage} from "../hooks/useBoxscorePage";
import type {DesignBoxscoreTeam} from "../hooks/useBoxscorePage";
import {designPath} from "../designRoutes";
import DesignGameSummary from "../shared/DesignGameSummary";
import DesignHeader from "../shared/DesignHeader";
import PageState from "../shared/PageState";

const playerName = (player: Player) => `${player.firstName} ${player.familyName}`;
const didPlay = (player: Player) => player.statistics.minutes !== "";
const teamScore = (team: DesignBoxscoreTeam) => team.statistics?.points ?? team.score;
const signed = (value: number) => (value > 0 ? `+${value}` : String(value));

const profileHref = (player: Player) =>
  `https://www.nba.com/player/${formatPlayerNameLink({...player, nameI: playerName(player)})}`;

const topPerformers = (team: DesignBoxscoreTeam, count: number) =>
  [...team.players]
    .filter(didPlay)
    .sort((a, b) => b.statistics.points - a.statistics.points)
    .slice(0, count);

function RadarLeaders({game}: {game: {awayTeam: DesignBoxscoreTeam; homeTeam: DesignBoxscoreTeam}}) {
  const leaders = [game.awayTeam, game.homeTeam].flatMap((team) =>
    topPerformers(team, 2).map((player) => ({team, player})),
  );
  if (leaders.length === 0) return null;

  return (
    <section className="radar-leaders" aria-label="Top performers">
      <span className="radar-eyebrow">TOP PERFORMERS</span>
      <div className="radar-leaders__grid">
        {leaders.map(({team, player}) => (
          <article key={player.personId} className="radar-leader">
            <PlayerHeadshot player={player} />
            <div className="radar-leader__who">
              <small>{team.teamTricode}</small>
              <span>{playerName(player)}</span>
            </div>
            <strong>{player.statistics.points}<b>PTS</b></strong>
            <em>{player.statistics.reboundsTotal} REB · {player.statistics.assists} AST</em>
          </article>
        ))}
      </div>
    </section>
  );
}

function RadarStatline({player}: {player: Player}) {
  const s = player.statistics;
  const pairs: Array<[string, string | number]> = [
    ["FG", `${s.fieldGoalsMade}-${s.fieldGoalsAttempted}`],
    ["3PT", `${s.threePointersMade}-${s.threePointersAttempted}`],
    ["FT", `${s.freeThrowsMade}-${s.freeThrowsAttempted}`],
    ["OREB", s.reboundsOffensive],
    ["DREB", s.reboundsDefensive],
    ["STL", s.steals],
    ["BLK", s.blocks],
    ["TO", s.turnovers],
    ["PF", s.foulsPersonal],
    ["+/-", signed(s.plusMinusPoints)],
  ];

  return (
    <div className="radar-statline">
      {pairs.map(([label, value]) => (
        <span key={label}>{label} <strong>{value}</strong></span>
      ))}
      <a href={profileHref(player)} target="_blank" rel="noopener noreferrer">
        Full profile <ExternalLink aria-hidden="true" />
      </a>
    </div>
  );
}

function RadarLedger({team}: {team: DesignBoxscoreTeam}) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const toggle = (personId: number) =>
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(personId)) next.delete(personId);
      else next.add(personId);
      return next;
    });

  return (
    <section className="radar-ledger" aria-label={`${team.teamCity} ${team.teamName} player statistics`}>
      <table>
        <thead>
          <tr><th>PLAYER</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th></tr>
        </thead>
        <tbody>
          {team.players.map((player) => {
            if (!didPlay(player)) {
              return (
                <tr key={player.personId} className="radar-ledger__dnp">
                  <th scope="row">
                    <span className="radar-ledger__player">
                      <PlayerHeadshot player={player} />
                      <span className="radar-ledger__name">
                        <span>{playerName(player)}</span>
                        <small>{player.position || player.jerseyNum}</small>
                      </span>
                    </span>
                  </th>
                  <td colSpan={4}>{player.comment || "DNP — Coach’s Decision"}</td>
                </tr>
              );
            }
            const isOpen = expanded.has(player.personId);
            return (
              <Fragment key={player.personId}>
                <tr className={isOpen ? "is-open" : undefined}>
                  <th scope="row">
                    <button
                      type="button"
                      className="radar-ledger__player"
                      aria-expanded={isOpen}
                      aria-controls={`radar-detail-${player.personId}`}
                      onClick={() => toggle(player.personId)}
                    >
                      <PlayerHeadshot player={player} />
                      <span className="radar-ledger__name">
                        <span>{playerName(player)}</span>
                        <small>{player.position || player.jerseyNum}</small>
                      </span>
                      <ChevronDown aria-hidden="true" className="radar-ledger__chevron" />
                    </button>
                  </th>
                  <td>{formatMinutesPlayed(player.statistics.minutes)}</td>
                  <td>{player.statistics.points}</td>
                  <td>{player.statistics.reboundsTotal}</td>
                  <td>{player.statistics.assists}</td>
                </tr>
                {isOpen && (
                  <tr id={`radar-detail-${player.personId}`} className="radar-ledger__detail">
                    <td colSpan={5}><RadarStatline player={player} /></td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function BoxscorePage() {
  const state = useBoxscorePage();
  const [side, setSide] = useState<"away" | "home">("away");
  const game = state.game;
  const activeTeam = game ? (side === "away" ? game.awayTeam : game.homeTeam) : null;

  return (
    <main className="concept-page concept-boxscore-page">
      {state.summary && (
        <div className="radar-scorebar">
          <span>{state.summary.awayTeam.teamTricode}</span>
          <strong>{state.summary.awayTeam.score}</strong>
          <em>{state.summary.gameStatusText}</em>
          <strong>{state.summary.homeTeam.score}</strong>
          <span>{state.summary.homeTeam.teamTricode}</span>
        </div>
      )}
      <DesignHeader designId="design-2" section="boxscore" />
      <div className="concept-back-row"><Link to={designPath("design-2", "/")}><ChevronLeft aria-hidden="true" /> Scoreboard</Link><span>OFFICIAL BOX SCORE</span></div>
      {state.isLoading ? <PageState kind="loading" /> : state.isError ? <PageState kind="error" title="Box score unavailable" /> : (
        <>
          {state.summary && <DesignGameSummary summary={state.summary} />}
          {game && activeTeam ? (
            <>
              <RadarLeaders game={game} />
              <div className="radar-team-switch" role="group" aria-label="Choose team box score">
                {([["away", game.awayTeam], ["home", game.homeTeam]] as const).map(([key, team]) => (
                  <button key={key} type="button" aria-pressed={side === key} onClick={() => setSide(key)}>
                    {team.teamTricode} <strong>{teamScore(team)}</strong>
                  </button>
                ))}
              </div>
              <RadarLedger key={activeTeam.teamId} team={activeTeam} />
            </>
          ) : <PageState kind="empty" title="Player ledger unavailable" detail="The game summary is still available above." />}
        </>
      )}
      <footer className="concept-footer"><span>NBA SCOREZ</span><span>Game ID {state.gameId}</span></footer>
    </main>
  );
}

export default BoxscorePage;

import {Link} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import type {PlayoffBracketModel, RenderSeries} from "@/utils/playoffBracketModel";
import {buildSeriesSlug, seasonToYear} from "@/utils/seriesSlug";
import {designPath} from "../designRoutes";
import type {AlternateDesignId} from "../types";

interface DesignBracketProps {
  designId: AlternateDesignId;
  model: PlayoffBracketModel;
  revealedRounds: Set<number>;
  revealRound: (round: number) => void;
  hideRound: (round: number) => void;
  canRevealRound: (round: number) => boolean;
}

function SeriesCard({designId, model, series, revealed}: {
  designId: AlternateDesignId;
  model: PlayoffBracketModel;
  series: RenderSeries;
  revealed: boolean;
}) {
  const slug = buildSeriesSlug(series, model.series);
  return (
    <Link className="concept-series-card" to={designPath(designId, `/playoffs/${seasonToYear(model.season)}/${slug}`)}>
      {series.targetWins && <small>BEST OF {series.targetWins * 2 - 1}</small>}
      {series.teams.map((team, index) => {
        const wins = series.wins[team.id] || 0;
        const winner = revealed && series.winnerTeamId === team.id;
        return (
          <div key={`${series.seriesKey}-${team.id || index}`} className={winner ? "is-winner" : ""}>
            <TeamLogos teamName={team.tricode} teamId={team.id} size={34} tricode={team.tricode} />
            <span>{team.tricode || "TBD"}</span>
            {revealed && <strong>{wins}</strong>}
          </div>
        );
      })}
    </Link>
  );
}

function DesignBracket({designId, model, revealedRounds, revealRound, hideRound, canRevealRound}: DesignBracketProps) {
  return (
    <section className="concept-bracket">
      <div className="concept-bracket__round-controls" aria-label="Playoff result controls">
        {model.rounds.filter((round) => canRevealRound(round.round)).map((round) => {
          const revealed = revealedRounds.has(round.round);
          return (
            <button key={round.round} type="button" aria-pressed={revealed} onClick={() => revealed ? hideRound(round.round) : revealRound(round.round)}>
              <span>{String(round.round).padStart(2, "0")}</span>
              {revealed ? `Hide ${round.label}` : `Reveal ${round.label}`}
            </button>
          );
        })}
      </div>

      <div className="concept-bracket__groups">
        {model.groups.map((group) => {
          const groupSeries = model.series.filter((series) => series.bracketGroupId === group.id);
          if (groupSeries.length === 0) return null;
          return (
            <section key={group.id} className="concept-bracket__group">
              <header><span>{group.kind}</span><h2>{group.label}</h2></header>
              <div className="concept-bracket__rounds">
                {model.rounds.filter((round) => canRevealRound(round.round) && groupSeries.some((series) => series.round === round.round)).map((round) => (
                  <section className="concept-bracket__round" key={round.round}>
                    <h3>{round.label}</h3>
                    <div>
                      {groupSeries
                        .filter((series) => series.round === round.round)
                        .sort((a, b) => a.bracketOrder - b.bracketOrder)
                        .map((series) => <SeriesCard key={series.seriesKey} designId={designId} model={model} series={series} revealed={revealedRounds.has(round.round)} />)}
                    </div>
                  </section>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </section>
  );
}

export default DesignBracket;

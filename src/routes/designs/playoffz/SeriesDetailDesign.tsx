import {useMemo} from "react";
import {Switch} from "@adobe/react-spectrum";
import {Link, useParams, useSearchParams} from "react-router-dom";
import TeamLogos from "@/components/TeamLogos";
import StatusPill from "@/components/designs/StatusPill";
import StudioShell from "@/components/designs/StudioShell";
import {TEAM_COLORS} from "@/constants/teamColors";
import {formatGameDate, generateWatchLink} from "@/helpers/helpers";
import {usePlayoffData} from "@/hooks/usePlayoffData";
import {buildPlayoffBracketModel} from "@/utils/playoffBracketModel";
import {findSeriesBySlug, yearToSeason} from "@/utils/seriesSlug";

function SeriesDetailDesign() {
  const {year, seriesSlug} = useParams<{year: string; seriesSlug: string}>();
  const isValidYear = !!year && /^\d{4}$/.test(year);
  const season = isValidYear ? yearToSeason(year) : null;
  const [searchParams, setSearchParams] = useSearchParams();
  const isRevealed = searchParams.get("revealed") === "true";
  const {data, isLoading, error} = usePlayoffData(season);
  const model = useMemo(
    () => (data ? buildPlayoffBracketModel(data) : null),
    [data],
  );

  const setIsRevealed = (value: boolean) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set("revealed", "true");
        else next.delete("revealed");
        return next;
      },
      {replace: true},
    );
  };

  if (!isValidYear) {
    return (
      <StudioShell
        title="Series unavailable"
        eyebrow="Invalid playoff year"
        backTo="/designs/playoffz"
        backLabel="Preview bracket"
        variant="editorial"
      >
        <div className="rounded-lg border border-red-300 bg-red-50 p-8 text-red-800 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-200">
          Invalid season year.
        </div>
      </StudioShell>
    );
  }

  if (isLoading) {
    return (
      <StudioShell
        title="Loading matchup feature"
        eyebrow="Series detail"
        backTo={`/designs/playoffz${season ? `?season=${season}` : ""}`}
        backLabel="Preview bracket"
        variant="editorial"
      >
        <div className="rounded-lg border border-white/70 bg-white/75 p-10 text-center font-bold dark:border-white/10 dark:bg-slate-950/60">
          Loading series...
        </div>
      </StudioShell>
    );
  }

  if (error || !data || !model) {
    return (
      <StudioShell
        title="Series unavailable"
        eyebrow="Series detail"
        backTo={`/designs/playoffz${season ? `?season=${season}` : ""}`}
        backLabel="Preview bracket"
        variant="editorial"
      >
        <div className="rounded-lg border border-red-300 bg-red-50 p-8 text-red-800 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-200">
          Error loading series: {String(error)}
        </div>
      </StudioShell>
    );
  }

  const series = findSeriesBySlug(seriesSlug ?? "", model.series);

  if (!series) {
    return (
      <StudioShell
        title="Series not found"
        eyebrow="Series detail"
        backTo={`/designs/playoffz?season=${season}`}
        backLabel="Preview bracket"
        variant="editorial"
      >
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-8 text-amber-900 dark:border-amber-400/40 dark:bg-amber-500/10 dark:text-amber-100">
          This matchup is not available for the selected season.
        </div>
      </StudioShell>
    );
  }

  const [team1, team2] = series.teams;
  const team1Wins = series.wins[team1.id] || 0;
  const team2Wins = series.wins[team2.id] || 0;
  const team1Color = TEAM_COLORS[team1.id] ?? "#1D428A";
  const team2Color = TEAM_COLORS[team2.id] ?? "#C8102E";
  const seasonYear = parseInt((model.season ?? data.season).split("-")[0]);

  return (
    <StudioShell
      title={`${team1.tricode} vs ${team2.tricode}`}
      eyebrow="Editorial matchup feature"
      backTo={`/designs/playoffz?season=${season}`}
      backLabel="Preview bracket"
      variant="editorial"
    >
      <section className="grid gap-5">
        <div
          className="overflow-hidden rounded-lg border border-white/55 text-white shadow-2xl"
          style={{
            background: `linear-gradient(120deg, ${team1Color}, rgba(15,23,42,0.92) 48%, ${team2Color})`,
          }}
        >
          <div className="grid gap-6 bg-black/20 p-5 backdrop-blur-sm sm:p-8 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
            <div className="flex items-center gap-4">
              <TeamLogos
                teamName={team1.name}
                teamId={team1.id}
                size={76}
                tricode={team1.tricode}
              />
              <div>
                <p className="text-xs font-black uppercase tracking-[0.24em] text-white/70">
                  {series.roundName}
                </p>
                <h2 className="text-4xl font-black tracking-tight">
                  {team1.tricode}
                </h2>
              </div>
            </div>
            <div className="rounded-lg border border-white/20 bg-white/12 px-6 py-4 text-center">
              <p className="text-xs font-black uppercase tracking-[0.24em] text-white/70">
                {data.season} playoffs
              </p>
              <p className="mt-2 font-mono text-5xl font-black tabular-nums">
                {isRevealed ? `${team1Wins}-${team2Wins}` : "VS"}
              </p>
              {isRevealed && series.winnerTeamTricode && (
                <p className="mt-2 text-sm font-bold uppercase tracking-[0.18em]">
                  {series.winnerTeamTricode} wins
                </p>
              )}
            </div>
            <div className="flex items-center justify-start gap-4 lg:justify-end lg:text-right">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.24em] text-white/70">
                  {series.targetWins ? `Best of ${series.targetWins * 2 - 1}` : "Series"}
                </p>
                <h2 className="text-4xl font-black tracking-tight">
                  {team2.tricode}
                </h2>
              </div>
              <TeamLogos
                teamName={team2.name}
                teamId={team2.id}
                size={76}
                tricode={team2.tricode}
              />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/70 bg-white/75 px-4 py-3 shadow-lg dark:border-white/10 dark:bg-slate-950/65">
          <StatusPill tone={isRevealed ? "final" : "warning"}>
            {isRevealed ? "Results revealed" : "Results hidden"}
          </StatusPill>
          <Switch isSelected={isRevealed} onChange={setIsRevealed}>
            <span className="text-slate-950 dark:text-slate-50">
              {isRevealed ? "Hide Results" : "Show Results"}
            </span>
          </Switch>
        </div>

        <div className="rounded-lg border border-white/70 bg-white/78 p-3 shadow-xl dark:border-white/10 dark:bg-slate-950/65 sm:p-5">
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                Game timeline
              </p>
              <h2 className="text-2xl font-black">Series games</h2>
            </div>
            <Link
              to={`/designs/playoffz?season=${season}`}
              className="hidden rounded-md border border-slate-300 px-3 py-2 text-sm font-bold hover:border-sky-500 hover:text-sky-700 dark:border-white/15 dark:hover:border-sky-300 dark:hover:text-sky-200 sm:inline-flex"
            >
              Bracket
            </Link>
          </div>
          {series.games.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-slate-500 dark:border-white/15 dark:text-slate-400">
              No games are listed for this series.
            </div>
          ) : (
            <div className="grid gap-3">
              {series.games.map((game, index) => {
                const shouldShowWatch = seasonYear >= 2012;
                const watchLink = generateWatchLink(
                  game.awayTeam.tricode,
                  game.homeTeam.tricode,
                  game.gameId,
                );
                const homeWon =
                  isRevealed && game.homeTeam.score > game.awayTeam.score;
                const awayWon =
                  isRevealed && game.awayTeam.score > game.homeTeam.score;

                return (
                  <div
                    key={game.gameId}
                    className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50/80 p-3 dark:border-white/10 dark:bg-white/5 sm:grid-cols-[96px_120px_1fr_auto] sm:items-center"
                  >
                    <StatusPill tone="neutral">Game {index + 1}</StatusPill>
                    <span className="text-sm font-bold text-slate-500 dark:text-slate-400">
                      {formatGameDate(game.date)}
                    </span>
                    <div className="text-base font-black">
                      {isRevealed ? (
                        <>
                          <span className={awayWon ? "text-emerald-600 dark:text-emerald-300" : ""}>
                            {game.awayTeam.tricode} {game.awayTeam.score}
                          </span>
                          <span className="px-2 text-slate-400">at</span>
                          <span className={homeWon ? "text-emerald-600 dark:text-emerald-300" : ""}>
                            {game.homeTeam.score} {game.homeTeam.tricode}
                          </span>
                        </>
                      ) : (
                        <span>
                          {game.awayTeam.tricode} at {game.homeTeam.tricode}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2 text-sm font-bold">
                      {shouldShowWatch && (
                        <a
                          href={watchLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="rounded-md border border-slate-300 px-3 py-2 hover:border-sky-500 hover:text-sky-700 dark:border-white/15 dark:hover:border-sky-300 dark:hover:text-sky-200"
                        >
                          Watch
                        </a>
                      )}
                      {isRevealed && (
                        <Link
                          to={`/designs/boxscore-bento/${game.gameId}`}
                          className="rounded-md bg-slate-950 px-3 py-2 text-white hover:bg-sky-700 dark:bg-white dark:text-slate-950 dark:hover:bg-sky-200"
                        >
                          Box score
                        </Link>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>
    </StudioShell>
  );
}

export default SeriesDetailDesign;

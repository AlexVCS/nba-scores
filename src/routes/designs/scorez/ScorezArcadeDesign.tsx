import {useEffect, useState} from "react";
import {Switch} from "@adobe/react-spectrum";
import {useQuery} from "@tanstack/react-query";
import {Link, useSearchParams} from "react-router";
import GameDatePicker from "@/components/GameDatePicker";
import TeamLogos from "@/components/TeamLogos";
import StudioShell from "@/components/designs/StudioShell";
import {generateWatchLink, getItem, setItem} from "@/helpers/helpers";
import {SCOREZ_PREVIEW_DATE} from "@/routes/designs/designDefaults";
import {getScores} from "@/services/nbaService";

type ArcadeGame = {
  gameId: string;
  gameStatus: number;
  gameStatusText: string;
  gameLabel: string;
  gameSubLabel: string;
  gameTimeUTC: string;
  homeTeam: {
    teamName: string;
    teamTricode: string;
    teamId: number;
    score: number;
  };
  awayTeam: {
    teamName: string;
    teamTricode: string;
    teamId: number;
    score: number;
  };
};

function canShowBoxscore(game: ArcadeGame) {
  const endOf1819Season = new Date("2019-06-15T00:00:00Z");
  return game.gameStatus !== 1 && new Date(game.gameTimeUTC) >= endOf1819Season;
}

function ArcadeTeamRow({
  team,
  score,
  showScore,
  winner,
}: {
  team: ArcadeGame["homeTeam"];
  score: number;
  showScore: boolean;
  winner: boolean;
}) {
  return (
    <div
      className={`grid grid-cols-[44px_1fr_auto] items-center gap-3 border border-amber-500/25 bg-black px-3 py-3 shadow-[inset_0_0_18px_rgba(245,158,11,0.12)] ${
        winner ? "text-emerald-300" : "text-amber-300"
      }`}
    >
      <span className="flex h-11 w-11 items-center justify-center rounded bg-zinc-950 ring-1 ring-amber-400/20">
        <TeamLogos
          teamName={team.teamName}
          teamId={team.teamId}
          size={34}
          tricode={team.teamTricode}
        />
      </span>
      <span className="min-w-0 truncate font-mono text-2xl font-black tracking-[0.18em] [text-shadow:0_0_12px_rgba(245,158,11,0.7)]">
        {team.teamTricode || "TBD"}
      </span>
      <span className="min-w-16 text-right font-mono text-4xl font-black tabular-nums text-orange-500 [text-shadow:0_0_18px_rgba(249,115,22,0.95)]">
        {showScore ? score : "--"}
      </span>
    </div>
  );
}

function ArcadeCard({game, showScores}: {game: ArcadeGame; showScores: boolean}) {
  const shouldShowScore = showScores && game.gameStatus !== 1;
  const homeWon = shouldShowScore && game.homeTeam.score > game.awayTeam.score;
  const awayWon = shouldShowScore && game.awayTeam.score > game.homeTeam.score;
  const watchGameLink = generateWatchLink(
    game.awayTeam.teamTricode,
    game.homeTeam.teamTricode,
    game.gameId,
  );

  return (
    <article className="rounded-md border-4 border-zinc-800 bg-zinc-950 p-2 shadow-[0_0_0_1px_rgba(245,158,11,0.38),0_24px_60px_rgba(0,0,0,0.55)]">
      <div className="border border-amber-500/25 bg-[linear-gradient(90deg,rgba(245,158,11,0.12),transparent,rgba(239,68,68,0.12))] px-3 py-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="font-mono text-xs font-black uppercase tracking-[0.28em] text-red-400">
            {game.gameStatusText}
          </span>
          <span className="font-mono text-xs font-black uppercase tracking-[0.22em] text-amber-500">
            {game.gameLabel ? `${game.gameLabel} ${game.gameSubLabel}` : "NBA SCOREZ"}
          </span>
        </div>
      </div>
      <div className="grid gap-2 py-2">
        <ArcadeTeamRow
          team={game.awayTeam}
          score={game.awayTeam.score}
          showScore={shouldShowScore}
          winner={awayWon}
        />
        <ArcadeTeamRow
          team={game.homeTeam}
          score={game.homeTeam.score}
          showScore={shouldShowScore}
          winner={homeWon}
        />
      </div>
      <div className="flex flex-wrap justify-end gap-2 border-t border-amber-500/20 pt-2 font-mono text-xs font-black uppercase tracking-[0.18em]">
        {canShowBoxscore(game) && shouldShowScore && (
          <Link
            to={`/designs/boxscore/${game.gameId}`}
            className="border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-amber-200 hover:bg-amber-500/20"
          >
            Box score
          </Link>
        )}
        <Link
          to={watchGameLink}
          target="_blank"
          className="border border-red-500/40 bg-red-500/10 px-3 py-2 text-red-200 hover:bg-red-500/20"
        >
          Watch
        </Link>
      </div>
    </article>
  );
}

function ScorezArcadeDesign() {
  const [searchParams, setSearchParams] = useSearchParams({date: ""});
  const dateParam = searchParams.get("date") || SCOREZ_PREVIEW_DATE;
  const [showScores, setShowScores] = useState(() => {
    const item = getItem("showScores");
    return item === undefined ? false : item;
  });

  useEffect(() => {
    if (!searchParams.get("date")) {
      setSearchParams({date: SCOREZ_PREVIEW_DATE}, {replace: true});
    }
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    setItem("showScores", showScores);
  }, [showScores]);

  const {isLoading, data, error} = useQuery({
    queryKey: ["design-arcade-games", dateParam],
    queryFn: () => getScores(dateParam) as Promise<{games: ArcadeGame[]}>,
  });

  const games = data?.games ?? [];
  const hasStartedGames = games.some((game) => game.gameStatus !== 1);

  return (
    <StudioShell
      title="Scorez Pixel Board"
      eyebrow="Preview route /designs/scorez-arcade"
      backTo="/"
      backLabel="Current Scorez"
      variant="arcade"
      actions={<GameDatePicker />}
    >
      <section className="grid gap-4 text-amber-100">
        <div className="grid gap-4 rounded-md border-4 border-zinc-800 bg-black/80 p-3 shadow-[inset_0_0_40px_rgba(245,158,11,0.08)] sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <p className="font-mono text-xs font-black uppercase tracking-[0.34em] text-red-400">
              Insert date to play
            </p>
            <p className="font-mono text-2xl font-black text-amber-300 [text-shadow:0_0_16px_rgba(245,158,11,0.65)]">
              {isLoading ? "LOADING..." : `${games.length} MATCHUPS`}
            </p>
          </div>
          {hasStartedGames && (
            <Switch isSelected={showScores} onChange={setShowScores}>
              <span className="text-amber-100">
                {showScores ? "Hide Scores" : "Show Scores"}
              </span>
            </Switch>
          )}
        </div>

        {isLoading && (
          <div className="rounded-md border border-amber-500/30 bg-black/80 p-8 text-center font-mono font-black">
            WARMING UP SCOREBOARD...
          </div>
        )}
        {error && (
          <div className="rounded-md border border-red-500/40 bg-red-950/50 p-8 text-center font-mono font-black text-red-200">
            SCOREBOARD ERROR: {String(error)}
          </div>
        )}
        {!isLoading && !error && games.length === 0 && (
          <div className="rounded-md border border-amber-500/30 bg-black/80 p-8 text-center font-mono font-black">
            NO GAMES ON THIS DATE
          </div>
        )}
        <div className="grid gap-5 xl:grid-cols-2">
          {games.map((game) => (
            <ArcadeCard key={game.gameId} game={game} showScores={showScores} />
          ))}
        </div>
      </section>
    </StudioShell>
  );
}

export default ScorezArcadeDesign;

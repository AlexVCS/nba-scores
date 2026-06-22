import {useEffect, useState} from "react";
import {Switch} from "@adobe/react-spectrum";
import {useQuery} from "@tanstack/react-query";
import {Link, useSearchParams} from "react-router";
import GameDatePicker from "@/components/GameDatePicker";
import TeamLogos from "@/components/TeamLogos";
import StatusPill from "@/components/designs/StatusPill";
import StudioShell from "@/components/designs/StudioShell";
import TeamMatchupStrip from "@/components/designs/TeamMatchupStrip";
import {TEAM_COLORS} from "@/constants/teamColors";
import {generateWatchLink, getItem, setItem} from "@/helpers/helpers";
import {SCOREZ_PREVIEW_DATE} from "@/routes/designs/designDefaults";
import {getScores} from "@/services/nbaService";

type GameData = {
  gameId: string;
  gameCode: string;
  gameStatus: number;
  gameLabel: string;
  gameSubLabel: string;
  gameTimeUTC: string;
  gameStatusText: string;
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

function getStatusTone(game: GameData) {
  if (game.gameStatus === 3) return "final";
  if (game.gameStatus === 2) return "live";
  return "scheduled";
}

function canShowBoxscore(game: GameData) {
  const endOf1819Season = new Date("2019-06-15T00:00:00Z");
  return game.gameStatus !== 1 && new Date(game.gameTimeUTC) >= endOf1819Season;
}

interface ScorezCardProps {
  game: GameData;
  showScores: boolean;
}

function ScorezCard({game, showScores}: ScorezCardProps) {
  const homeColor = TEAM_COLORS[game.homeTeam.teamId] ?? "#1D428A";
  const awayColor = TEAM_COLORS[game.awayTeam.teamId] ?? "#C8102E";
  const watchGameLink = generateWatchLink(
    game.awayTeam.teamTricode,
    game.homeTeam.teamTricode,
    game.gameId,
  );
  const shouldShowScores = showScores && game.gameStatus !== 1;
  const homeWon = shouldShowScores && game.homeTeam.score > game.awayTeam.score;
  const awayWon = shouldShowScores && game.awayTeam.score > game.homeTeam.score;

  return (
    <article className="group overflow-hidden rounded-lg border border-white/70 bg-white/82 shadow-xl shadow-slate-300/30 backdrop-blur transition duration-200 hover:-translate-y-0.5 hover:shadow-2xl dark:border-white/10 dark:bg-slate-950/72 dark:shadow-black/30">
      <div
        className="h-1.5"
        style={{
          background: `linear-gradient(90deg, ${awayColor}, ${homeColor})`,
        }}
      />
      <div className="flex items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3 dark:border-white/10">
        <StatusPill tone={getStatusTone(game)}>{game.gameStatusText}</StatusPill>
        {game.gameLabel && (
          <span className="truncate text-xs font-bold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
            {game.gameLabel}: {game.gameSubLabel}
          </span>
        )}
      </div>
      <div className="p-4 sm:p-5">
        <TeamMatchupStrip
          awayTeam={{
            teamId: game.awayTeam.teamId,
            teamName: game.awayTeam.teamName,
            teamTricode: game.awayTeam.teamTricode,
            score: game.awayTeam.score,
          }}
          homeTeam={{
            teamId: game.homeTeam.teamId,
            teamName: game.homeTeam.teamName,
            teamTricode: game.homeTeam.teamTricode,
            score: game.homeTeam.score,
          }}
          showScores={shouldShowScores}
          winnerTeamId={
            homeWon ? game.homeTeam.teamId : awayWon ? game.awayTeam.teamId : null
          }
        />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200/80 bg-slate-50/75 px-4 py-3 dark:border-white/10 dark:bg-white/5">
        <div className="flex items-center gap-2">
          <span
            className="h-3 w-3 rounded-full"
            style={{backgroundColor: awayColor}}
          />
          <span
            className="h-3 w-3 rounded-full"
            style={{backgroundColor: homeColor}}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm font-bold">
          {canShowBoxscore(game) && shouldShowScores && (
            <Link
              to={`/designs/boxscore/${game.gameId}`}
              className="rounded-md bg-slate-950 px-3 py-2 text-white hover:bg-sky-700 dark:bg-white dark:text-slate-950 dark:hover:bg-sky-200"
            >
              Box score
            </Link>
          )}
          <Link
            to={watchGameLink}
            target="_blank"
            className="rounded-md border border-slate-300 px-3 py-2 hover:border-sky-500 hover:text-sky-700 dark:border-white/15 dark:hover:border-sky-300 dark:hover:text-sky-200"
          >
            Watch
          </Link>
        </div>
      </div>
    </article>
  );
}

function ScorezDesign() {
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
    queryKey: ["design-games", dateParam],
    queryFn: () => getScores(dateParam) as Promise<{games: GameData[]}>,
  });

  const games = data?.games ?? [];
  const hasStartedGames = games.some((game) => game.gameStatus !== 1);

  return (
    <StudioShell
      title="Scorez Broadcast Desk"
      eyebrow="Preview route /designs/scorez"
      backTo="/"
      backLabel="Current Scorez"
      variant="studio"
      actions={<GameDatePicker />}
    >
      <section className="grid gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/70 bg-white/72 px-4 py-3 shadow-lg shadow-slate-300/20 backdrop-blur dark:border-white/10 dark:bg-slate-950/62 dark:shadow-black/20">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
              Daily board
            </p>
            <p className="text-lg font-black">
              {isLoading
                ? "Loading matchups"
                : `${games.length} games loaded`}
            </p>
          </div>
          {hasStartedGames && (
            <Switch isSelected={showScores} onChange={setShowScores}>
              <span className="text-slate-950 dark:text-slate-50">
                {showScores ? "Hide Scores" : "Show Scores"}
              </span>
            </Switch>
          )}
        </div>

        {isLoading && (
          <div className="rounded-lg border border-white/70 bg-white/75 p-8 text-center font-bold dark:border-white/10 dark:bg-slate-950/60">
            Loading the board...
          </div>
        )}
        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 p-8 text-center font-bold text-red-800 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-200">
            Error loading scores: {String(error)}
          </div>
        )}
        {!isLoading && !error && games.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white/65 p-8 text-center dark:border-white/15 dark:bg-slate-950/45">
            <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-slate-950 text-white dark:bg-white dark:text-slate-950">
              <TeamLogos teamId={0} size={36} teamName="NBA" tricode="NBA" />
            </div>
            <h2 className="text-xl font-black">No games scheduled</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Try another date to load the broadcast board.
            </p>
          </div>
        )}
        <div className="grid gap-4 lg:grid-cols-2">
          {games.map((game) => (
            <ScorezCard key={game.gameId} game={game} showScores={showScores} />
          ))}
        </div>
      </section>
    </StudioShell>
  );
}

export default ScorezDesign;

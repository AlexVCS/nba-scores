import {useQuery} from "@tanstack/react-query";
import {Link, useParams} from "react-router";
import StudioShell from "@/components/designs/StudioShell";
import {Team} from "@/helpers/helpers";
import {getBoxScores, getGameSummary} from "@/services/nbaService";
import StudioGameSummary from "./StudioGameSummary";
import StudioPlayerTable from "./StudioPlayerTable";

interface BoxscoreTeam extends Team {
  teamId: number;
  teamTricode: string;
  teamCity: string;
  statistics?: {points: number};
}

interface SummaryTeam {
  teamId: number;
  teamTricode: string;
  teamName: string;
  score: string;
  periods: Array<{period: number; score: string}>;
}

interface GameSummaryData {
  homeTeam: SummaryTeam;
  awayTeam: SummaryTeam;
  period: number;
  gameStatusText: string;
}

function buildTeamFromBoxscore(team: BoxscoreTeam): SummaryTeam {
  return {
    teamId: team.teamId ?? 0,
    teamTricode: team.teamTricode ?? "",
    teamName: `${team.teamCity ?? ""} ${team.teamName ?? ""}`.trim(),
    score: String(team.statistics?.points ?? team.score ?? ""),
    periods: [],
  };
}

function BoxscoreDesign() {
  const {gameId = ""} = useParams();

  const boxscoreQuery = useQuery({
    queryKey: ["design-boxscore", gameId],
    queryFn: () =>
      getBoxScores(gameId) as Promise<{
        game: {
          homeTeam: BoxscoreTeam;
          awayTeam: BoxscoreTeam;
          gameStatusText?: string;
        };
      }>,
  });

  const gameSummaryQuery = useQuery({
    queryKey: ["design-gameSummary", gameId],
    queryFn: () => getGameSummary(gameId) as Promise<GameSummaryData>,
  });

  if (boxscoreQuery.isLoading) {
    return (
      <StudioShell
        title="Loading analytics desk"
        eyebrow="Preview route /designs/boxscore"
        backTo="/designs/scorez"
        backLabel="Preview Scorez"
        variant="analytics"
      >
        <div className="rounded-lg border border-white/70 bg-white/75 p-10 text-center font-bold dark:border-white/10 dark:bg-slate-950/60">
          Loading boxscore...
        </div>
      </StudioShell>
    );
  }

  if (boxscoreQuery.isError || !boxscoreQuery.data) {
    return (
      <StudioShell
        title="Boxscore unavailable"
        eyebrow="Preview route /designs/boxscore"
        backTo="/designs/scorez"
        backLabel="Preview Scorez"
        variant="analytics"
      >
        <div className="rounded-lg border border-red-300 bg-red-50 p-8 text-red-800 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-200">
          Error loading boxscore data.
        </div>
      </StudioShell>
    );
  }

  const {game} = boxscoreQuery.data;
  const summaryData =
    gameSummaryQuery.data ??
    (!gameSummaryQuery.isLoading
      ? {
          homeTeam: buildTeamFromBoxscore(game.homeTeam),
          awayTeam: buildTeamFromBoxscore(game.awayTeam),
          period: 0,
          gameStatusText: game.gameStatusText ?? "Unknown",
        }
      : null);

  return (
    <StudioShell
      title="Pro Analytics Desk"
      eyebrow={`Preview route /designs/boxscore/${gameId}`}
      backTo="/designs/scorez"
      backLabel="Preview Scorez"
      variant="analytics"
      actions={
        <div className="flex flex-wrap gap-2">
          <Link
            to="/designs/scorez"
            className="rounded-md border border-slate-300 bg-white/75 px-3 py-2 text-sm font-bold hover:border-teal-500 hover:text-teal-700 dark:border-white/15 dark:bg-slate-950/55 dark:hover:border-teal-300 dark:hover:text-teal-200"
          >
            Studio Scorez
          </Link>
          <Link
            to="/designs/scorez-arcade"
            className="rounded-md border border-slate-300 bg-white/75 px-3 py-2 text-sm font-bold hover:border-amber-500 hover:text-amber-700 dark:border-white/15 dark:bg-slate-950/55 dark:hover:border-amber-300 dark:hover:text-amber-200"
          >
            Arcade Scorez
          </Link>
        </div>
      }
    >
      <section className="grid gap-5">
        {summaryData ? (
          <StudioGameSummary game={summaryData} />
        ) : (
          <div className="rounded-lg border border-white/70 bg-white/75 p-6 text-center font-bold dark:border-white/10 dark:bg-slate-950/60">
            Loading game summary...
          </div>
        )}
        <StudioPlayerTable team={game.awayTeam} />
        <StudioPlayerTable team={game.homeTeam} />
      </section>
    </StudioShell>
  );
}

export default BoxscoreDesign;

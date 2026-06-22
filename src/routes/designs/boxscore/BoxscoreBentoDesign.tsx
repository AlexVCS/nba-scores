import {useQuery} from "@tanstack/react-query";
import {Link, useParams} from "react-router";
import DesignEmptyState from "@/components/designs/patterns/DesignEmptyState";
import SkeletonBlock from "@/components/designs/patterns/SkeletonBlock";
import StudioShell from "@/components/designs/StudioShell";
import {Team} from "@/helpers/helpers";
import {getBoxScores, getGameSummary} from "@/services/nbaService";
import BentoPlayerStream from "./BentoPlayerStream";
import BentoScoreSummary from "./BentoScoreSummary";
import BentoStatLeaders from "./BentoStatLeaders";
import BentoTeamTables from "./BentoTeamTables";

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

function BoxscoreBentoDesign() {
  const {gameId = ""} = useParams();

  const boxscoreQuery = useQuery({
    queryKey: ["design-bento-boxscore", gameId],
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
    queryKey: ["design-bento-gameSummary", gameId],
    queryFn: () => getGameSummary(gameId) as Promise<GameSummaryData>,
  });

  return (
    <StudioShell
      title="Motion Bento Analytics Board"
      eyebrow={`Preview route /designs/boxscore-bento/${gameId}`}
      backTo="/designs/scorez-masonry"
      backLabel="Masonry Scorez"
      variant="analytics"
      actions={
        <Link
          to="/designs/scorez-coverflow"
          className="rounded-full border border-teal-300 bg-white/70 px-4 py-2 text-sm font-black uppercase tracking-[0.16em] text-teal-900 hover:bg-teal-50 active:scale-[0.98] dark:border-teal-300/20 dark:bg-white/10 dark:text-teal-100 dark:hover:bg-teal-300/10"
        >
          Coverflow
        </Link>
      }
    >
      {boxscoreQuery.isLoading && (
        <section className="grid gap-5 lg:grid-cols-12">
          <SkeletonBlock className="h-80 lg:col-span-7" />
          <SkeletonBlock className="h-80 lg:col-span-5" />
          <SkeletonBlock className="h-72 lg:col-span-4" />
          <SkeletonBlock className="h-96 lg:col-span-8" />
        </section>
      )}

      {(boxscoreQuery.isError || (!boxscoreQuery.isLoading && !boxscoreQuery.data)) && (
        <DesignEmptyState
          title="Bento board could not load"
          message="The boxscore endpoint did not return usable data for this game."
          actionTo="/designs/scorez-masonry"
          actionLabel="Back to schedule wall"
          className="border-teal-300 bg-teal-50 text-teal-950 dark:border-teal-300/25 dark:bg-teal-300/10 dark:text-teal-100"
        />
      )}

      {boxscoreQuery.data && (
        <section className="grid gap-5 lg:grid-cols-12">
          <BentoScoreSummary
            game={
              gameSummaryQuery.data ??
              (!gameSummaryQuery.isLoading
                ? {
                    homeTeam: buildTeamFromBoxscore(boxscoreQuery.data.game.homeTeam),
                    awayTeam: buildTeamFromBoxscore(boxscoreQuery.data.game.awayTeam),
                    period: 0,
                    gameStatusText:
                      boxscoreQuery.data.game.gameStatusText ?? "Unknown",
                  }
                : {
                    homeTeam: buildTeamFromBoxscore(boxscoreQuery.data.game.homeTeam),
                    awayTeam: buildTeamFromBoxscore(boxscoreQuery.data.game.awayTeam),
                    period: 0,
                    gameStatusText: "Loading summary",
                  })
            }
          />
          <BentoStatLeaders
            teams={[
              boxscoreQuery.data.game.awayTeam,
              boxscoreQuery.data.game.homeTeam,
            ]}
          />
          <BentoPlayerStream
            teams={[
              boxscoreQuery.data.game.awayTeam,
              boxscoreQuery.data.game.homeTeam,
            ]}
          />
          <BentoTeamTables
            teams={[
              boxscoreQuery.data.game.awayTeam,
              boxscoreQuery.data.game.homeTeam,
            ]}
          />
        </section>
      )}
    </StudioShell>
  );
}

export default BoxscoreBentoDesign;

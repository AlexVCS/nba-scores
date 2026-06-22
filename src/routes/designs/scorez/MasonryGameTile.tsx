import {motion} from "framer-motion";
import {Link} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import BreathingStatusDot from "@/components/designs/motion/BreathingStatusDot";
import MagneticTextButton from "@/components/designs/motion/MagneticTextButton";
import {cascadeItemVariants} from "@/components/designs/motion/cascadeVariants";
import {TEAM_COLORS} from "@/constants/teamColors";
import {generateWatchLink} from "@/helpers/helpers";

export type DesignScoreGame = {
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

function canShowBoxscore(game: DesignScoreGame) {
  const endOf1819Season = new Date("2019-06-15T00:00:00Z");
  return game.gameStatus !== 1 && new Date(game.gameTimeUTC) >= endOf1819Season;
}

function getTone(game: DesignScoreGame) {
  if (game.gameStatus === 2) return "live";
  if (game.gameStatus === 3) return "final";
  return "scheduled";
}

interface MasonryGameTileProps {
  game: DesignScoreGame;
  showScores: boolean;
  featured?: boolean;
}

function TeamPlate({
  team,
  score,
  showScore,
  align = "left",
  winner = false,
}: {
  team: DesignScoreGame["homeTeam"];
  score: number;
  showScore: boolean;
  align?: "left" | "right";
  winner?: boolean;
}) {
  return (
    <div
      className={`grid grid-cols-[auto_1fr_auto] items-center gap-3 border-t border-slate-200 py-4 first:border-t-0 dark:border-white/10 ${
        align === "right" ? "text-right" : ""
      }`}
    >
      <TeamLogos
        teamName={team.teamName}
        teamId={team.teamId}
        size={44}
        tricode={team.teamTricode}
      />
      <div className="min-w-0">
        <p className="truncate text-xl font-black tracking-tight">
          {team.teamTricode || "TBD"}
        </p>
        <p className="truncate text-xs font-bold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
          {team.teamName}
        </p>
      </div>
      <p
        className={`font-mono text-3xl font-black tabular-nums ${
          winner ? "text-rose-700 dark:text-rose-300" : "text-slate-950 dark:text-slate-50"
        }`}
      >
        {showScore ? score : "--"}
      </p>
    </div>
  );
}

function MasonryGameTile({game, showScores, featured = false}: MasonryGameTileProps) {
  const awayColor = TEAM_COLORS[game.awayTeam.teamId] ?? "#881337";
  const homeColor = TEAM_COLORS[game.homeTeam.teamId] ?? "#881337";
  const shouldShowScore = showScores && game.gameStatus !== 1;
  const awayWon = shouldShowScore && game.awayTeam.score > game.homeTeam.score;
  const homeWon = shouldShowScore && game.homeTeam.score > game.awayTeam.score;
  const watchLink = generateWatchLink(
    game.awayTeam.teamTricode,
    game.homeTeam.teamTricode,
    game.gameId,
  );

  return (
    <motion.article
      variants={cascadeItemVariants}
      className={`group rounded-[1.5rem] border border-slate-200 bg-white/80 p-4 shadow-[0_24px_60px_-34px_rgba(63,63,70,0.45)] transition-transform active:scale-[0.99] dark:border-white/10 dark:bg-zinc-950/72 ${
        featured ? "md:col-span-2 md:row-span-2 md:p-6" : ""
      }`}
      style={{
        boxShadow: `0 24px 60px -42px ${awayColor}, inset 0 1px 0 rgba(255,255,255,0.24)`,
      }}
    >
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.22em] text-rose-700 dark:text-rose-300">
            <BreathingStatusDot tone={getTone(game)} />
            <span>{game.gameStatusText}</span>
          </div>
          {game.gameLabel && (
            <p className="mt-2 text-sm font-bold text-slate-500 dark:text-slate-400">
              {game.gameLabel}: {game.gameSubLabel}
            </p>
          )}
        </div>
        <div
          className="h-12 w-12 rounded-full border border-slate-200 dark:border-white/10"
          style={{
            background: `linear-gradient(135deg, ${awayColor}, ${homeColor})`,
          }}
        />
      </div>

      <div className="divide-y-0">
        <TeamPlate
          team={game.awayTeam}
          score={game.awayTeam.score}
          showScore={shouldShowScore}
          winner={awayWon}
        />
        <TeamPlate
          team={game.homeTeam}
          score={game.homeTeam.score}
          showScore={shouldShowScore}
          winner={homeWon}
          align="right"
        />
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
        <Link
          to={watchLink}
          target="_blank"
          className="text-sm font-black uppercase tracking-[0.16em] text-slate-600 underline-offset-4 hover:text-rose-700 hover:underline dark:text-slate-300 dark:hover:text-rose-200"
        >
          Watch
        </Link>
        {canShowBoxscore(game) && shouldShowScore && (
          <MagneticTextButton
            to={`/designs/boxscore-bento/${game.gameId}`}
            className="border-rose-200 bg-rose-50 text-rose-800 hover:border-rose-400 dark:border-rose-300/20 dark:bg-rose-300/10 dark:text-rose-100"
          >
            Boxscore
          </MagneticTextButton>
        )}
      </div>
    </motion.article>
  );
}

export default MasonryGameTile;

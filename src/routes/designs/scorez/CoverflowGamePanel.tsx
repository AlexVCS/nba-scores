import {motion} from "framer-motion";
import {Link} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import BreathingStatusDot from "@/components/designs/motion/BreathingStatusDot";
import MagneticTextButton from "@/components/designs/motion/MagneticTextButton";
import {TEAM_COLORS} from "@/constants/teamColors";
import {generateWatchLink} from "@/helpers/helpers";
import type {DesignScoreGame} from "./MasonryGameTile";

interface CoverflowGamePanelProps {
  game: DesignScoreGame;
  showScores: boolean;
  isFocused: boolean;
  onFocus: () => void;
}

function canShowBoxscore(game: DesignScoreGame) {
  const endOf1819Season = new Date("2019-06-15T00:00:00Z");
  return game.gameStatus !== 1 && new Date(game.gameTimeUTC) >= endOf1819Season;
}

function getTone(game: DesignScoreGame) {
  if (game.gameStatus === 2) return "live";
  if (game.gameStatus === 3) return "final";
  return "scheduled";
}

function CoverflowGamePanel({
  game,
  showScores,
  isFocused,
  onFocus,
}: CoverflowGamePanelProps) {
  const awayColor = TEAM_COLORS[game.awayTeam.teamId] ?? "#075985";
  const homeColor = TEAM_COLORS[game.homeTeam.teamId] ?? "#075985";
  const shouldShowScore = showScores && game.gameStatus !== 1;
  const watchLink = generateWatchLink(
    game.awayTeam.teamTricode,
    game.homeTeam.teamTricode,
    game.gameId,
  );

  return (
    <motion.article
      layout
      onMouseEnter={onFocus}
      onFocus={onFocus}
      tabIndex={0}
      className={`snap-center shrink-0 rounded-[2rem] border bg-white/85 p-5 shadow-[0_24px_60px_-38px_rgba(2,132,199,0.55)] outline-none transition-transform duration-300 active:scale-[0.98] dark:bg-zinc-950/74 ${
        isFocused
          ? "w-[86vw] border-sky-400 md:w-[520px] md:scale-100"
          : "w-[78vw] border-slate-200 opacity-80 md:w-[360px] md:scale-[0.92] dark:border-white/10"
      }`}
      style={{
        boxShadow: `0 28px 70px -48px ${awayColor}, inset 0 1px 0 rgba(255,255,255,0.22)`,
      }}
    >
      <div className="mb-8 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.22em] text-sky-700 dark:text-sky-300">
          <BreathingStatusDot tone={getTone(game)} />
          <span>{game.gameStatusText}</span>
        </div>
        <div
          className="h-8 w-20 rounded-full border border-slate-200 dark:border-white/10"
          style={{background: `linear-gradient(90deg, ${awayColor}, ${homeColor})`}}
        />
      </div>

      <div className="grid gap-6">
        {[game.awayTeam, game.homeTeam].map((team) => (
          <div
            key={`${game.gameId}-${team.teamId}-${team.teamTricode}`}
            className="grid grid-cols-[auto_1fr_auto] items-center gap-4"
          >
            <TeamLogos
              teamName={team.teamName}
              teamId={team.teamId}
              size={54}
              tricode={team.teamTricode}
            />
            <div className="min-w-0">
              <p className="truncate text-3xl font-black tracking-tighter">
                {team.teamTricode || "TBD"}
              </p>
              <p className="truncate text-xs font-bold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                {team.teamName}
              </p>
            </div>
            <p className="font-mono text-4xl font-black tabular-nums">
              {shouldShowScore ? team.score : "--"}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <Link
          to={watchLink}
          target="_blank"
          className="text-sm font-black uppercase tracking-[0.16em] text-slate-600 underline-offset-4 hover:text-sky-700 hover:underline dark:text-slate-300 dark:hover:text-sky-200"
        >
          Watch
        </Link>
        {canShowBoxscore(game) && shouldShowScore && (
          <MagneticTextButton
            to={`/designs/boxscore-bento/${game.gameId}`}
            className="border-sky-200 bg-sky-50 text-sky-800 hover:border-sky-400 dark:border-sky-300/20 dark:bg-sky-300/10 dark:text-sky-100"
          >
            Boxscore
          </MagneticTextButton>
        )}
      </div>
    </motion.article>
  );
}

export default CoverflowGamePanel;

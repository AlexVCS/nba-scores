import {motion} from "framer-motion";
import MagneticTextButton from "@/components/designs/motion/MagneticTextButton";
import {cascadeItemVariants} from "@/components/designs/motion/cascadeVariants";
import {formatGameDate, generateWatchLink} from "@/helpers/helpers";
import type {RenderSeries} from "@/utils/playoffBracketModel";

interface SeriesGameLedgerProps {
  series: RenderSeries;
  isRevealed: boolean;
  season: string;
}

function SeriesGameLedger({series, isRevealed, season}: SeriesGameLedgerProps) {
  const seasonYear = Number.parseInt(season.split("-")[0], 10);

  return (
    <section className="grid gap-4">
      {series.games.map((game, index) => {
        const watchLink = generateWatchLink(
          game.awayTeam.tricode,
          game.homeTeam.tricode,
          game.gameId,
        );
        const shouldShowWatch = seasonYear >= 2012;
        const homeWon = isRevealed && game.homeTeam.score > game.awayTeam.score;
        const awayWon = isRevealed && game.awayTeam.score > game.homeTeam.score;

        return (
          <motion.article
            key={game.gameId}
            variants={cascadeItemVariants}
            className="grid gap-4 rounded-[1.5rem] border border-amber-200 bg-white/78 p-4 shadow-[0_20px_55px_-42px_rgba(180,83,9,0.5)] dark:border-amber-300/15 dark:bg-zinc-950/68 md:grid-cols-[150px_minmax(0,1fr)_auto] md:items-center"
          >
            <div>
              <p className="text-xs font-black uppercase tracking-[0.22em] text-amber-700 dark:text-amber-300">
                Game {index + 1}
              </p>
              <p className="mt-1 text-2xl font-black tracking-tighter">
                {formatGameDate(game.date)}
              </p>
            </div>
            <div className="font-black">
              {isRevealed ? (
                <p className="text-2xl tracking-tight">
                  <span className={awayWon ? "text-amber-700 dark:text-amber-300" : ""}>
                    {game.awayTeam.tricode} {game.awayTeam.score}
                  </span>
                  <span className="px-3 text-slate-400">at</span>
                  <span className={homeWon ? "text-amber-700 dark:text-amber-300" : ""}>
                    {game.homeTeam.score} {game.homeTeam.tricode}
                  </span>
                </p>
              ) : (
                <p className="text-2xl tracking-tight">
                  {game.awayTeam.tricode} at {game.homeTeam.tricode}
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-2 md:justify-end">
              {shouldShowWatch && (
                <MagneticTextButton
                  href={watchLink}
                  className="border-amber-200 bg-amber-50 text-amber-900 hover:border-amber-400 dark:border-amber-300/20 dark:bg-amber-300/10 dark:text-amber-100"
                >
                  Watch
                </MagneticTextButton>
              )}
              {isRevealed && (
                <MagneticTextButton
                  to={`/designs/boxscore-bento/${game.gameId}`}
                  className="border-zinc-300 bg-zinc-950 text-white hover:border-zinc-500 dark:border-white/15 dark:bg-white dark:text-zinc-950"
                >
                  Boxscore
                </MagneticTextButton>
              )}
            </div>
          </motion.article>
        );
      })}
    </section>
  );
}

export default SeriesGameLedger;

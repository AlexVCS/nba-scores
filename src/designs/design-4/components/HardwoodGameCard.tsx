import type {CSSProperties} from "react";
import {ExternalLink} from "lucide-react";
import {Link} from "react-router";
import TeamLogos from "@/components/TeamLogos";
import {generateWatchLink} from "@/helpers/helpers";
import type {GameData} from "@/helpers/helpers";
import {designPath} from "../../designRoutes";

interface HardwoodGameCardProps {
  game: GameData;
  showScores: boolean;
  index: number;
}

interface TeamProps {
  game: GameData;
  side: "home" | "away";
  showScore: boolean;
}

function Team({game, side, showScore}: TeamProps) {
  const team = side === "home" ? game.homeTeam : game.awayTeam;
  const scoreboardTeam = team.teamId > 0 ? team.teamTricode : "TBD";

  return (
    <div className="grid items-center justify-items-center text-center">
      <span className="mb-[7px] text-[8px] font-bold tracking-[.22em] text-hw-muted">{side === "home" ? "HOME" : "AWAY"}</span>
      <TeamLogos teamName={team.teamName} teamId={team.teamId} size={58} tricode={team.teamTricode} />
      <div>
        <strong className="mt-1.5 block text-2xl leading-none font-extrabold uppercase">{scoreboardTeam}</strong>
        <small className="mt-[3px] block max-w-[120px] text-[9px] text-hw-muted uppercase max-[700px]:hidden">{team.teamName}</small>
      </div>
      {showScore && (
        <b className="mt-2 text-5xl leading-[.9] font-extrabold tracking-[-.02em] text-hw-ink tabular-nums dark:text-hw-accent max-[700px]:text-[40px]">
          {team.score}
        </b>
      )}
    </div>
  );
}

function HardwoodGameCard({game, showScores, index}: HardwoodGameCardProps) {
  const started = game.gameStatus !== 1;
  const reveal = showScores && started;
  const boxscore = reveal && game.boxscoreAvailable === true && game.gameId.length > 0;
  const watch = generateWatchLink(game.awayTeam.teamTricode, game.homeTeam.teamTricode, game.gameId);

  return (
    <article
      style={{"--card-index": index} as CSSProperties}
      className="relative animate-hw-enter overflow-hidden rounded-hw border border-hw-line bg-hw-surface shadow-hw-card [animation-delay:calc(var(--card-index)*70ms)] transition-[transform,box-shadow] duration-[180ms] [transition-timing-function:ease] hover:-translate-y-[3px] hover:shadow-hw-card-hover motion-reduce:animate-none motion-reduce:transition-none motion-reduce:hover:translate-y-0"
    >
      <header className="grid min-h-[42px] grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3.5 border-b border-hw-line px-3.5 py-[9px]">
        <strong className="col-start-2 text-center text-xs font-bold uppercase">{game.gameStatusText}</strong>
        {game.gameLabel && (
          <small className="col-start-3 min-w-0 justify-self-end text-right text-[9px] font-bold tracking-[.18em] text-hw-muted max-[700px]:hidden">
            {game.gameLabel} · {game.gameSubLabel}
          </small>
        )}
      </header>
      <div className="grid min-h-[180px] grid-cols-[1fr_auto_1fr] items-center gap-3.5 px-[18px] py-6 max-[700px]:px-2.5">
        <Team game={game} side="away" showScore={reveal} />
        <span className="grid size-8 place-items-center rounded-full bg-hw-accent text-[9px] font-extrabold text-hw-accent-contrast">VS</span>
        <Team game={game} side="home" showScore={reveal} />
      </div>
      {!game.gameStatusText.includes(":") && (
        <footer className="flex min-h-[42px] items-center justify-end gap-5 border-t border-hw-line px-3.5 py-2">
          {boxscore && (
            <Link className="inline-flex items-center gap-1.5 text-[10px] font-extrabold tracking-[.1em] uppercase no-underline hover:text-hw-accent-ink" to={designPath("design-4", `/games/${game.gameId}/boxscore`)}>
              Box score
            </Link>
          )}
          <a className="inline-flex items-center gap-1.5 text-[10px] font-extrabold tracking-[.1em] uppercase no-underline hover:text-hw-accent-ink" href={watch} target="_blank" rel="noopener noreferrer">
            Watch <ExternalLink className="w-3" aria-hidden="true" />
          </a>
        </footer>
      )}
    </article>
  );
}

export default HardwoodGameCard;

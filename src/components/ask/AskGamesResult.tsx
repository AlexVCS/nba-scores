import type {AskGamesResult as AskGamesResultData} from "@/services/ask/types";
import AskGameCard from "./AskGameCard";
import AskLinks from "./AskLinks";
import AskRevealButton from "./AskRevealButton";
import {formatAskDate} from "./askFormat";
import {RESULT_GROUP, safeGame} from "./askSpoilers";
import {askCap, type AskRevealControls} from "./askStyles";

interface AskGamesResultProps {
  result: AskGamesResultData;
  controls: AskRevealControls;
}

function AskGamesResult({result, controls}: AskGamesResultProps) {
  const revealed = controls.isRevealed(RESULT_GROUP);
  const count = result.total_games;

  return (
    <section aria-label="Games">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <span className="text-[15px] font-extrabold">{count} {count === 1 ? "game" : "games"}</span>
        <AskRevealButton group={RESULT_GROUP} controls={controls} label={count === 1 ? "score" : `all ${count} scores`} />
      </div>
      <ul className="grid grid-cols-2 gap-3 max-[700px]:grid-cols-1">
        {result.days.flatMap(day => day.games).map((item, index) => (
          <li key={item.game.gameId} className="grid content-start gap-1.5">
            <h4 className={`${askCap} px-0.5 text-hw-ink!`}>{formatAskDate(item.date, {weekday: "short", month: "short", day: "numeric"})}</h4>
            <AskGameCard
              game={safeGame(item.game, item.spoilers, revealed)}
              showScores={revealed}
              date={item.date}
              index={index}
            />
            {/* The card already links to the boxscore; show the item's other verified links. */}
            <AskLinks
              links={item.links.filter(link => link.kind !== "boxscore")}
              revealed={revealed}
              label={`${item.game.awayTeam.teamTricode} at ${item.game.homeTeam.teamTricode} links`}
              compact
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

export default AskGamesResult;

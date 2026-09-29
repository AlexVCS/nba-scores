import type {AskGamesResult as AskGamesResultData} from "@/services/ask/types";
import AskGameCard from "./AskGameCard";
import AskLinks from "./AskLinks";
import {formatAskDate} from "./askFormat";
import {askCap} from "./askStyles";

interface AskGamesResultProps {
  result: AskGamesResultData;
  resultsHidden: boolean;
}

function AskGamesResult({result, resultsHidden}: AskGamesResultProps) {
  const count = result.total_games.value;
  const games = result.days.flatMap(day => day.games);

  return (
    <section aria-label="Games">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <span className="text-[15px] font-extrabold">{count} {count === 1 ? "game" : "games"}</span>
      </div>
      <ul className="grid grid-cols-2 gap-3 max-[700px]:grid-cols-1">
        {games.map((item, index) => (
          <li key={item.game.gameId} className="grid content-start gap-1.5">
            <h4 className={`${askCap} px-0.5 text-hw-ink!`}>{formatAskDate(item.date, {weekday: "short", month: "short", day: "numeric"})}</h4>
            <AskGameCard game={item.game} showScores date={item.date} index={index} />
            {/* The card already links to the boxscore; show the item's other verified links. */}
            <AskLinks
              links={item.links.filter(link => link.kind !== "boxscore")}
              resultsHidden={resultsHidden}
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

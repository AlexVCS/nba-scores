import {useLocation} from "react-router";
import type {GameData} from "@/helpers/helpers";
import GameCard from "@/routes/games/GameCard";
import HardwoodGameCard from "@/designs/design-1/components/HardwoodGameCard";

interface AskGameCardProps {
  game: GameData;
  showScores: boolean;
  date: string;
  index: number;
}

/** The scores page's own game card for the design being viewed, so links and logo fallbacks match. */
function AskGameCard({game, showScores, date, index}: AskGameCardProps) {
  const {pathname} = useLocation();
  if (/^\/design-1(?=\/|$)/.test(pathname)) {
    return <HardwoodGameCard game={game} showScores={showScores} index={index} dateParam={date} />;
  }
  return (
    <div className="rounded-[12px] bg-slate-50 dark:bg-neutral-950">
      <GameCard game={game} showScores={showScores} dateParam={date} />
    </div>
  );
}

export default AskGameCard;

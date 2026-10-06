import type {GameData} from "@/helpers/helpers";
import HardwoodGameCard from "@/designs/design-1/components/HardwoodGameCard";

interface AskGameCardProps {
  game: GameData;
  showScores: boolean;
  date: string;
  index: number;
}

/** The scores page's own game card, so links and logo fallbacks match. */
function AskGameCard({game, showScores, date, index}: AskGameCardProps) {
  return <HardwoodGameCard game={game} showScores={showScores} index={index} dateParam={date} showTricodes={false} />;
}

export default AskGameCard;

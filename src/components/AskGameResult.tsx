import {Eye, EyeOff} from "lucide-react";
import {useLocation} from "react-router";
import HardwoodGameCard from "@/designs/design-1/components/HardwoodGameCard";
import {detectDesignId} from "@/designs/designRoutes";
import type {AskItem} from "@/helpers/ask";
import GameCard from "@/routes/games/GameCard";
import {ASK_REVEAL, ASK_NOTICE, ASK_VEIL, ASK_VEIL_LINE, ASK_INTERPRETATION, ASK_INTERPRETATION_CHIP} from "./askStyles";

interface AskGameResultProps {
  item: AskItem;
  interpretation: string[];
  visible: boolean;
  revealed: boolean;
  showReveal: boolean;
  onToggle: () => void;
}

function AskGameResult({item, interpretation, visible, revealed, showReveal, onToggle}: AskGameResultProps) {
  const {pathname} = useLocation();
  const hardwood = detectDesignId(pathname) === "design-1";
  const date = item.fields.find(field => field.label === "Date")?.value;
  const dateParam = typeof date === "string" ? date : "";
  const game = item.game;

  return (
    <li className="w-full min-w-0 [&_article]:w-full">
      {showReveal && (
        <div className="mb-2 flex justify-end">
          <button type="button" className={ASK_REVEAL} aria-pressed={revealed} onClick={onToggle}>
            {revealed ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
            {revealed ? "Hide result" : "Reveal result"}
          </button>
        </div>
      )}
      {visible ? (
        game && /^\d+$/.test(game.gameId) ? (
          hardwood
            ? <HardwoodGameCard game={game} showScores={true} index={0} dateParam={dateParam} />
            : <GameCard game={game} showScores={true} dateParam={dateParam} />
        ) : <p className={ASK_NOTICE}>Search again to load this game's card.</p>
      ) : (
        <div className="min-h-[260px] rounded-[10px] border border-[var(--ask-line)] bg-[var(--ask-surface)] p-6 shadow-[var(--hw-shadow-card)]" aria-hidden="true">
          <div className={ASK_VEIL}><span className={ASK_VEIL_LINE} /><span className={ASK_VEIL_LINE} /><span className={ASK_VEIL_LINE} /></div>
        </div>
      )}
      {interpretation.length > 0 && (
        <p className={`${ASK_INTERPRETATION} text-[var(--hw-court,var(--ask-muted))]`}>
          <span>Interpreted as:</span>
          {interpretation.map(part => <span className={ASK_INTERPRETATION_CHIP} key={part}>{part}</span>)}
        </p>
      )}
    </li>
  );
}

export default AskGameResult;

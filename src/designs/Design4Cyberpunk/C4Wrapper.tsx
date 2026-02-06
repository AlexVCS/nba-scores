import {useTheme} from "@/hooks/useTheme";
import GameDatePicker from "@/components/GameDatePicker";
import C4Header from "./C4Header";
import C4Games from "./C4Games";
import "./design4.css";

const C4Wrapper = () => {
  const {theme} = useTheme();

  return (
    <div className={`cyber-container ${theme}`}>
      <C4Header />
      <div className="cyber-date-section">
        <GameDatePicker />
      </div>
      <C4Games />
    </div>
  );
};

export default C4Wrapper;

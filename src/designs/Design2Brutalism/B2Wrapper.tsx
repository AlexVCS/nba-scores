import {useTheme} from "@/hooks/useTheme";
import GameDatePicker from "@/components/GameDatePicker";
import B2Header from "./B2Header";
import B2Games from "./B2Games";
import "./design2.css";

const B2Wrapper = () => {
  const {theme} = useTheme();

  return (
    <div className={`brutal-container ${theme}`}>
      <B2Header />
      <div className="brutal-date-section">
        <label className="brutal-date-label">Select Date</label>
        <GameDatePicker />
      </div>
      <B2Games />
    </div>
  );
};

export default B2Wrapper;

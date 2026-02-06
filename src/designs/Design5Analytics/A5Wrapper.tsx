import {useTheme} from "@/hooks/useTheme";
import GameDatePicker from "@/components/GameDatePicker";
import A5Header from "./A5Header";
import A5Games from "./A5Games";
import "./design5.css";

const A5Wrapper = () => {
  const {theme} = useTheme();

  return (
    <div className={`analytics-container ${theme}`}>
      <A5Header />
      <div className="analytics-dashboard">
        <div className="analytics-date-section">
          <span className="analytics-date-label">Select Date:</span>
          <GameDatePicker />
        </div>
      </div>
      <A5Games />
    </div>
  );
};

export default A5Wrapper;

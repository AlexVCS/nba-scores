import {useTheme} from "@/hooks/useTheme";
import DarkModeToggle from "@/components/DarkModeToggle";
import GameDatePicker from "@/components/GameDatePicker";
import LED1Header from "./LED1Header";
import LED1Games from "./LED1Games";
import "./design1.css";

const LED1Wrapper = () => {
  const {theme} = useTheme();

  return (
    <div className={`led-container ${theme}`}>
      <div style={{position: "absolute", top: "1rem", right: "1rem", zIndex: 10}}>
        <DarkModeToggle />
      </div>
      <LED1Header />
      <div className="led-date-picker">
        <GameDatePicker />
      </div>
      <LED1Games />
    </div>
  );
};

export default LED1Wrapper;

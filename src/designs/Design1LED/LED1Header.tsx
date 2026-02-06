import {Link} from "react-router-dom";
import {useTheme} from "@/hooks/useTheme";
import "./design1.css";

const LED1Header = () => {
  const {theme} = useTheme();

  return (
    <header className="led-header">
      <Link to="/" className="led-back-link">
        ← Designs
      </Link>
      
      <img
        className="led-logo"
        src={theme === "dark" ? "/images/dark-mode-logo.webp" : "/images/light-mode-logo.webp"}
        alt="NBA Scorez Logo"
      />
    </header>
  );
};

export default LED1Header;

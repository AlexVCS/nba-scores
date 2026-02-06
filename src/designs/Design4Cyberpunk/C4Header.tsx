import {Link} from "react-router-dom";
import {useTheme} from "@/hooks/useTheme";
import DarkModeToggle from "@/components/DarkModeToggle";
import "./design4.css";

const C4Header = () => {
  const {theme} = useTheme();

  return (
    <header className="cyber-header">
      <Link to="/" className="cyber-back-link">
        ← Designs
      </Link>
      
      <div style={{position: "absolute", top: "1rem", right: "1rem", zIndex: 10}}>
        <DarkModeToggle />
      </div>
      
      <img
        className="cyber-logo"
        src={theme === "dark" ? "/images/dark-mode-logo.webp" : "/images/light-mode-logo.webp"}
        alt="NBA Scorez Logo"
      />
    </header>
  );
};

export default C4Header;

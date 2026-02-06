import {Link} from "react-router-dom";
import {useTheme} from "@/hooks/useTheme";
import DarkModeToggle from "@/components/DarkModeToggle";
import "./design5.css";

const A5Header = () => {
  const {theme} = useTheme();

  return (
    <header className="analytics-header">
      <div className="analytics-header-left">
        <img
          className="analytics-logo"
          src={theme === "dark" ? "/images/dark-mode-logo.webp" : "/images/light-mode-logo.webp"}
          alt="NBA Scorez Logo"
        />
        <Link to="/" className="analytics-back-link">
          ← All Designs
        </Link>
      </div>
      <DarkModeToggle />
    </header>
  );
};

export default A5Header;

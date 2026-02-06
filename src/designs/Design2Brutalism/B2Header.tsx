import {Link} from "react-router-dom";
import {useTheme} from "@/hooks/useTheme";
import DarkModeToggle from "@/components/DarkModeToggle";
import "./design2.css";

const B2Header = () => {
  const {theme} = useTheme();

  return (
    <header className="brutal-header">
      <img
        className="brutal-logo"
        src={theme === "dark" ? "/images/dark-mode-logo.webp" : "/images/light-mode-logo.webp"}
        alt="NBA Scorez Logo"
      />
      
      <nav className="brutal-nav">
        <Link to="/" className="brutal-back-link">
          ← Designs
        </Link>
        <DarkModeToggle />
      </nav>
    </header>
  );
};

export default B2Header;

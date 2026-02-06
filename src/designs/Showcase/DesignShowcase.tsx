import {Link} from "react-router-dom";
import {useTheme} from "@/hooks/useTheme";
import DarkModeToggle from "@/components/DarkModeToggle";
import "./showcase.css";

const designs = [
  {
    id: "1",
    path: "/1",
    title: "LED Scoreboard",
    description: "Retro stadium digital display with glowing amber scores, scanline effects, and authentic LED aesthetics.",
  },
  {
    id: "2",
    path: "/2",
    title: "Minimalist Brutalism",
    description: "Raw, stripped-down anti-design with stark borders, aggressive negative space, and industrial typography.",
  },
  {
    id: "4",
    path: "/4",
    title: "Neon Cyberpunk",
    description: "80s futuristic meets sports tech with holographic effects, neon glows, and animated gradients.",
  },
  {
    id: "5",
    path: "/5",
    title: "Sports Analytics",
    description: "Modern data visualization dashboard with clean panels, team color gradients, and stats-forward design.",
  },
];

const DesignShowcase = () => {
  const {theme} = useTheme();

  return (
    <div className={`showcase-container ${theme}`}>
      <div className="showcase-toggle-wrapper">
        <DarkModeToggle />
      </div>

      <header className="showcase-header">
        <img
          className="showcase-logo"
          src={theme === "dark" ? "/images/dark-mode-logo.webp" : "/images/light-mode-logo.webp"}
          alt="NBA Scorez Logo"
        />
        <h1 className="showcase-title">Design Gallery</h1>
        <p className="showcase-subtitle">4 unique visual directions</p>
      </header>

      <div className="showcase-grid">
        {designs.map((design) => (
          <Link
            key={design.id}
            to={design.path}
            className="showcase-card"
            data-design={design.id}
          >
            <div className="showcase-card-preview">
              <div className="showcase-preview-content">
                <div className="preview-element">
                  <div className="preview-score">88 - 92</div>
                </div>
              </div>
            </div>
            <div className="showcase-card-content">
              <div className="showcase-card-number">DESIGN {design.id}</div>
              <h2 className="showcase-card-title">{design.title}</h2>
              <p className="showcase-card-description">{design.description}</p>
            </div>
            <span className="showcase-card-arrow">→</span>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default DesignShowcase;

import {Switch} from "@adobe/react-spectrum";
import {useGamesData} from "../shared/useGamesData";
import A5GameCard from "./A5GameCard";
import "./design5.css";

const A5Games = () => {
  const {isLoading, data, error, showScores, setShowScores} = useGamesData();

  if (isLoading) {
    return <div className="analytics-loading">Loading data...</div>;
  }

  if (error) {
    return <div className="analytics-no-games">Error loading games</div>;
  }

  if (!data) {
    return <div className="analytics-no-games">No data available</div>;
  }

  const {games} = data;

  const liveGames = games.filter(g => g.gameStatus === 2).length;
  const completedGames = games.filter(g => g.gameStatus === 3).length;
  const upcomingGames = games.filter(g => g.gameStatus === 1).length;

  return (
    <div className="analytics-dashboard">
      {/* Stats Overview */}
      <div className="analytics-stats-bar">
        <div className="analytics-stat-card">
          <div className="analytics-stat-label">Total Games</div>
          <div className="analytics-stat-value">{games.length}</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-label">Live Now</div>
          <div className="analytics-stat-value">{liveGames}</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-label">Completed</div>
          <div className="analytics-stat-value">{completedGames}</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-label">Upcoming</div>
          <div className="analytics-stat-value">{upcomingGames}</div>
        </div>
      </div>

      {/* Toggle */}
      {games.some((game) => game.gameStatus !== 1) && (
        <div className="analytics-toggle">
          <Switch isSelected={showScores} onChange={setShowScores}>
            <span className="analytics-toggle-text">
              {showScores ? "Hide Scores" : "Show Scores"}
            </span>
          </Switch>
        </div>
      )}

      {/* Games Section */}
      <div className="analytics-section-header">
        <h2 className="analytics-section-title">Today's Matchups</h2>
        <span className="analytics-section-badge">{games.length} games</span>
      </div>

      {games.length === 0 ? (
        <div className="analytics-no-games">No games scheduled for today</div>
      ) : (
        <div className="analytics-games-grid">
          {games.map((game) => (
            <A5GameCard
              key={game.gameId}
              game={game}
              showScores={showScores}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default A5Games;

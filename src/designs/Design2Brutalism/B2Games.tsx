import {Switch} from "@adobe/react-spectrum";
import {useGamesData} from "../shared/useGamesData";
import B2GameCard from "./B2GameCard";
import "./design2.css";

const B2Games = () => {
  const {isLoading, data, error, showScores, setShowScores} = useGamesData();

  if (isLoading) {
    return <div className="brutal-loading">Loading...</div>;
  }

  if (error) {
    return <div className="brutal-no-games">Error loading games</div>;
  }

  if (!data) {
    return <div className="brutal-no-games">No data received</div>;
  }

  const {games} = data;

  return (
    <>
      {games.some((game) => game.gameStatus !== 1) && (
        <div className="brutal-toggle">
          <Switch isSelected={showScores} onChange={setShowScores}>
            <span className="brutal-toggle-text">
              {showScores ? "Hide Scores" : "Show Scores"}
            </span>
          </Switch>
        </div>
      )}

      <div className="brutal-games-section">
        <h2 className="brutal-section-title">Today's Games</h2>
        
        {games.length === 0 ? (
          <div className="brutal-no-games">No games scheduled</div>
        ) : (
          <div className="brutal-games-grid">
            {games.map((game) => (
              <B2GameCard
                key={game.gameId}
                game={game}
                showScores={showScores}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
};

export default B2Games;

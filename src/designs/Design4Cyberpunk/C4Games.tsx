import {Switch} from "@adobe/react-spectrum";
import {useGamesData} from "../shared/useGamesData";
import C4GameCard from "./C4GameCard";
import "./design4.css";

const C4Games = () => {
  const {isLoading, data, error, showScores, setShowScores} = useGamesData();

  if (isLoading) {
    return <div className="cyber-loading">Initializing...</div>;
  }

  if (error) {
    return <div className="cyber-no-games">Connection Error</div>;
  }

  if (!data) {
    return <div className="cyber-no-games">No Data Stream</div>;
  }

  const {games} = data;

  return (
    <>
      {games.some((game) => game.gameStatus !== 1) && (
        <div className="cyber-toggle">
          <Switch isSelected={showScores} onChange={setShowScores}>
            <span className="cyber-toggle-text">
              {showScores ? "Cloak Scores" : "Reveal Scores"}
            </span>
          </Switch>
        </div>
      )}

      {games.length === 0 ? (
        <div className="cyber-no-games">No Games In Queue</div>
      ) : (
        <div className="cyber-games-grid">
          {games.map((game) => (
            <C4GameCard
              key={game.gameId}
              game={game}
              showScores={showScores}
            />
          ))}
        </div>
      )}
    </>
  );
};

export default C4Games;

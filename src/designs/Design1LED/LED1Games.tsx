import {Switch} from "@adobe/react-spectrum";
import {useGamesData} from "../shared/useGamesData";
import LED1GameCard from "./LED1GameCard";
import "./design1.css";

const LED1Games = () => {
  const {isLoading, data, error, showScores, setShowScores} = useGamesData();

  if (isLoading) {
    return <div className="led-loading">Loading...</div>;
  }

  if (error) {
    return <div className="led-no-games">Error loading games</div>;
  }

  if (!data) {
    return <div className="led-no-games">No data received</div>;
  }

  const {games} = data;

  return (
    <>
      {games.some((game) => game.gameStatus !== 1) && (
        <div className="led-toggle">
          <Switch isSelected={showScores} onChange={setShowScores}>
            <span className="led-toggle-text">
              {showScores ? "Hide Scores" : "Show Scores"}
            </span>
          </Switch>
        </div>
      )}

      {games.length === 0 ? (
        <div className="led-no-games">No games scheduled</div>
      ) : (
        <section className={`led-games-grid ${games.length === 1 ? "single-game" : ""}`}>
          {games.map((game, index) => (
            <LED1GameCard
              key={game.gameId}
              game={game}
              showScores={showScores}
              index={index}
            />
          ))}
        </section>
      )}
    </>
  );
};

export default LED1Games;

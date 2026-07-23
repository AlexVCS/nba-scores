import GameCard from "./GameCard.jsx";
import {Switch} from "@adobe/react-spectrum";
import NoGamesQuickLinks from "@/components/NoGamesQuickLinks";
import {useScoresPage} from "@/designs/hooks/useScoresPage";

const Games = () => {
  const {isLoading, hasData, games, error, dateParam, showScores, setShowScores} = useScoresPage();

  if (isLoading) return <h1>Loading...</h1>;
  if (error) return <h1>{JSON.stringify(error)}</h1>;
  if (!hasData) return <h1>Didn't receive any games</h1>;
  return (
    <>
      {games.some((game) => game.gameStatus !== 1) && (
        <div className="flex justify-center items-center">
          <Switch isSelected={showScores} onChange={setShowScores}>
            <div className="dark:text-slate-50 text-neutral-950">
              {showScores ? "Hide Scores" : "Show Scores"}
            </div>
          </Switch>
        </div>
      )}
      {games.length === 0 ? (
        <NoGamesQuickLinks selectedDateParam={dateParam} />
      ) : (
        <section className="px-4 py-6">
          <div
            className={`grid gap-8 max-w-4xl mx-auto ${
              games.length === 1
                ? "grid-cols-1 place-items-center"
                : "grid-cols-1 lg:grid-cols-2"
            }`}
          >
            {games.map((gamedata) => (
              <GameCard
                key={gamedata.gameId}
                showScores={showScores}
                game={gamedata}
              />
            ))}
          </div>
        </section>
      )}
    </>
  );
};

export default Games;

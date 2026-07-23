import GameSummary from "@/components/GameSummary";
import DarkModeToggle from "@/components/DarkModeToggle";
import PlayerTable from "./PlayerTable";
// import InactivePlayers from "./InactivePlayers";
import {useBoxscorePage} from "@/designs/hooks/useBoxscorePage";

const Boxscore = () => {
  const {game, summary, isLoading, isError} = useBoxscorePage();

  if (isLoading) {
    return <h1>Loading...</h1>;
  }
  if (isError) {
    return <h1>Error loading boxscore data</h1>;
  }

  return (
    <div className="bg-slate-50 dark:bg-neutral-950 min-h-screen">
      <DarkModeToggle />
      {summary && <GameSummary game={summary} />}
      {game ? (
        <>
          <PlayerTable team={game.homeTeam} />
          <PlayerTable team={game.awayTeam} />
        </>
      ) : (
        <p className="px-4 pb-6 text-center text-sm text-neutral-700 dark:text-slate-300">
          Player boxscore is unavailable for this game.
        </p>
      )}
      {/* <InactivePlayers game={game} /> */}
    </div>
  );
};

export default Boxscore;

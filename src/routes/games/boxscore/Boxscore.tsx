import {Link} from "react-router";
import GameDetailsPanel from "@/designs/shared/GameDetailsPanel";
import GameSummary from "@/components/GameSummary";
import DarkModeToggle from "@/components/DarkModeToggle";
import PlayerTable from "./PlayerTable";
// import InactivePlayers from "./InactivePlayers";
import {useBoxscorePage} from "@/designs/hooks/useBoxscorePage";

const Boxscore = () => {
  const state = useBoxscorePage();
  const {game, summary} = state;

  return (
    <div className="min-h-screen bg-slate-50 text-neutral-900 dark:bg-neutral-950 dark:text-slate-50">
      <DarkModeToggle />
      <Link to={state.backPath} className="m-4 inline-block underline">Back to {state.backLabel.toLowerCase()}</Link>
      {state.isHidden || state.isPregame || state.isLoading || state.isError || state.isUnavailable ? <GameDetailsPanel state={state} /> : <>
      {summary && <GameSummary game={summary} />}
      {game ? (
        <>
          <PlayerTable team={game.homeTeam} />
          <PlayerTable team={game.awayTeam} />
        </>
      ) : (
        <p className="px-4 pb-6 text-center text-sm text-neutral-700 dark:text-slate-300">
          Player boxscore is unavailable for this game.
          {state.statsError && <button type="button" className="mx-auto mt-4 block min-h-12 cursor-pointer rounded border px-6" onClick={state.retry}>Try again</button>}
        </p>
      )}
      </>}
    </div>
  );
};

export default Boxscore;

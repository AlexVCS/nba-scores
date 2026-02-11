// import OvertimeHead from "@/components/Overtime";
import TeamLogos from "./TeamLogos";
import {ArrowIconRight, ArrowIconLeft} from "./ArrowIcon";

interface GameProps {
  game: {
    homeTeam: {
      teamId: number;
      teamTricode: string;
      teamName: string;
      periods: Array<{period: number; score: string}>;
      score: string;
    };
    awayTeam: {
      teamId: number;
      teamTricode: string;
      teamName: string;
      periods: Array<{period: number; score: string}>;
      score: string;
    };
    period: number;
    gameStatusText: string;
  };
}

const GameSummary: React.FC<GameProps> = ({ game }) => {
  return (
    <div className="flex flex-col md:grid md:grid-cols-3 items-center gap-3 md:gap-4 p-4 rounded-lg dark:text-slate-50 text-neutral-950">
      <div className="flex md:hidden w-full justify-center items-center gap-8">
        <div className="flex flex-col items-center">
          <TeamLogos
            teamName={game.homeTeam.teamName}
            teamId={game.homeTeam.teamId}
            size={48}
          />
          <h2 className="text-lg font-bold">
            {game.homeTeam.teamTricode}
          </h2>
          <div className="flex items-center justify-center relative">
            <h2 className="text-2xl font-bold">
              {game.homeTeam.score}
            </h2>
            {Number(game.homeTeam.score) > Number(game.awayTeam.score) && <ArrowIconRight />}
          </div>
        </div>

        <div className="flex flex-col items-center">
          <TeamLogos
            teamName={game.awayTeam.teamName}
            teamId={game.awayTeam.teamId}
            size={48}
          />
          <h2 className="text-lg  font-bold">
            {game.awayTeam.teamTricode}
          </h2>
          <div className="flex items-center justify-center relative">
            <h2 className="text-2xl font-bold">
              {game.awayTeam.score}
            </h2>
            {Number(game.awayTeam.score) > Number(game.homeTeam.score) && <ArrowIconLeft />}
          </div>
        </div>
      </div>

      <div className="hidden md:flex flex-col items-center">
        <TeamLogos
          teamName={game.homeTeam.teamName}
          teamId={game.homeTeam.teamId}
          size={48}
        />
        <h2 className="text-xl font-bold">
          {game.homeTeam.teamName}
        </h2>
        <div className="flex items-center justify-center relative">
          <h2 className="text-3xl font-bold mt-2">
            {game.homeTeam.score}
          </h2>
          {Number(game.homeTeam.score) > Number(game.awayTeam.score) && <ArrowIconRight />}
        </div>
      </div>

      <div className="w-full md:flex md:flex-col md:justify-center md:items-center px-4 md:px-0">
        <div className="flex flex-col items-center w-full">
          <table className="w-full text-sm md:text-base md:max-w-55">
            <thead>
              <tr>
                <th className="text-left pl-1.5 md:pl-3 pr-2 md:pr-8"></th>
                <th className="px-1 md:px-2 text-center">1</th>
                <th className="px-1 md:px-2 text-center">2</th>
                <th className="px-1 md:px-2 text-center">3</th>
                <th className="px-1 md:px-2 text-center">4</th>
                {game.homeTeam.periods.slice(4).map((p) => (
                  <th className="px-1 md:px-2 text-center" key={`ot-header-${p.period}`}>
                    OT{p.period - 4}
                  </th>
                ))}
                <th className="px-1 md:px-2 text-center">T</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="text-left pl-1.5 md:pl-3 pr-1">
                  {game.homeTeam.teamTricode}
                </td>
                {game.homeTeam.periods.map((period) => (
                  <td className="px-1 md:px-2 text-center" key={period.period}>
                    {period.score}
                  </td>
                ))}
                <td className="px-1 md:px-2 text-center font-bold">{game.homeTeam.score}</td>
              </tr>
              <tr>
                <td className="text-left pl-1.5 md:pl-3 pr-1">
                  {game.awayTeam.teamTricode}
                </td>
                {game.awayTeam.periods.map((period) => (
                  <td className="px-1 md:px-2 text-center" key={period.period}>
                    {period.score}
                  </td>
                ))}
                <td className="px-1 md:px-2 text-center font-bold">{game.awayTeam.score}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="hidden md:flex flex-col items-center">
        <TeamLogos
          teamName={game.awayTeam.teamName}
          teamId={game.awayTeam.teamId}
          size={48}
        />
        <h2 className="text-xl font-bold">
          {game.awayTeam.teamName}
        </h2>
        <div className="flex items-center justify-center relative">
          <h2 className="text-3xl font-bold mt-2">
            {game.awayTeam.score}
          </h2>
          {Number(game.awayTeam.score) > Number(game.homeTeam.score) && <ArrowIconLeft />}
        </div>
      </div>
    </div>
  );
};

export default GameSummary;

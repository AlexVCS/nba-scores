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
    <div className="grid grid-cols-3 items-center gap-4 p-4 rounded-lg dark:text-slate-50 text-neutral-950">
      <div className="flex flex-col items-center">
        <TeamLogos
          teamName={game.homeTeam.teamName}
          teamId={game.homeTeam.teamId}
          size={48}
        />
        <h2 className="text-xl font-bold hidden md:block">
          {game.homeTeam.teamName}
        </h2>
        <h2 className="text-xl font-bold block md:hidden">
          {game.homeTeam.teamTricode}
        </h2>
        <div className="flex items-center justify-center relative">
          <h2 className="text-2xl md:text-3xl font-bold mt-2 ">
            {game.homeTeam.score}
          </h2>
          {Number(game.homeTeam.score) > Number(game.awayTeam.score) && <ArrowIconRight />}
        </div>
      </div>

      <div className="flex flex-col justify-center items-center">
        <p className="md:hidden">{game.gameStatusText}</p>
        <div className="hidden md:flex md:flex-col md:items-center md:w-full">
          <p className="mb-4 text-center">{game.gameStatusText}</p>
          <table className="w-full max-w-55">
            <thead>
              <tr>
                <th className="text-left pl-3 pr-8"></th>
                <th className="px-2">1</th>
                <th className="px-2">2</th>
                <th className="px-2">3</th>
                <th className="px-2">4</th>
                {/* Overtime headers - render for periods > 4 */}
                {game.homeTeam.periods.slice(4).map((p) => (
                  <th className="px-2" key={`ot-header-${p.period}`}>
                    OT{p.period - 4}
                  </th>
                ))}
                <th className="px-2">T</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="text-left pl-3 pr-1">
                  {game.homeTeam.teamTricode}
                </td>
                {game.homeTeam.periods.map((period) => (
                  <td className="px-2" key={period.period}>
                    {period.score}
                  </td>
                ))}
                <td className="px-2 font-bold">{game.homeTeam.score}</td>
              </tr>
              <tr>
                <td className="text-left pl-3 pr-1">
                  {game.awayTeam.teamTricode}
                </td>
                {game.awayTeam.periods.map((period) => (
                  <td className="px-2" key={period.period}>
                    {period.score}
                  </td>
                ))}
                <td className="px-2 font-bold">{game.awayTeam.score}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex flex-col items-center">
        <TeamLogos
          teamName={game.awayTeam.teamName}
          teamId={game.awayTeam.teamId}
          size={48}
        />
        <h2 className="text-xl font-bold hidden md:block">
          {game.awayTeam.teamName}
        </h2>
        <h2 className="text-xl font-bold block md:hidden">
          {game.awayTeam.teamTricode}
        </h2>
        <div className="flex items-center justify-center relative">
          <h2 className="text-2xl md:text-3xl font-bold mt-2 ">
            {game.awayTeam.score}
          </h2>
          {Number(game.awayTeam.score) > Number(game.homeTeam.score) && <ArrowIconLeft />}
        </div>
      </div>
    </div>
  );
};

export default GameSummary;

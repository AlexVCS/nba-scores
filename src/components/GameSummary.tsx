import OvertimeHead from "@/components/Overtime";
import TeamLogos from "./TeamLogos";
import {ArrowIconRight, ArrowIconLeft} from "./ArrowIcon";

interface GameProps {
  game: {
    homeTeam: {
      teamTricode: string;
      teamName: string;
      periods: Array<{period: number; score: string}>;
      score: string;
    };
    awayTeam: {
      teamTricode: string;
      teamName: string;
      periods: Array<{period: number; score: string}>;
      score: string;
    };
    period: number;
    gameStatusText: string;
  };
}

const GameSummary: React.FC<GameProps> = ({game}) => {
  return (
    <div className="grid grid-cols-3 items-center gap-4 p-4 rounded-lg">
      {/* Home Team (Left) */}
      <div className="flex flex-col items-center">
        <TeamLogos teamTricode={game.homeTeam.teamTricode} size={48} />
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
          {game.homeTeam.score > game.awayTeam.score && <ArrowIconRight />}
        </div>
      </div>

      {/* Score Table (Center) */}
      <div className="flex justify-center items-center">
        <p>{game.gameStatusText}</p>
        <table className="w-full hidden md:table md:max-w-55">
          <thead>
            <tr>
              <th className="text-left pl-3 pr-8"></th>{" "}
              <th className="px-2">1</th>
              <th className="px-2">2</th>
              <th className="px-2">3</th>
              <th className="px-2">4</th>
              <OvertimeHead period={game.period} />
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

      {/* Away Team (Right) */}
      <div className="flex flex-col items-center">
        <TeamLogos teamTricode={game.awayTeam.teamTricode} size={48} />
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
          {game.awayTeam.score > game.homeTeam.score && <ArrowIconLeft />}
        </div>
      </div>
    </div>
  );
};

export default GameSummary;

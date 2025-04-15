import OvertimeHead from "@/components/Overtime";
import TeamLogos from "./TeamLogos";

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
  };
}

const GameSummary: React.FC<GameProps> = ({game}) => {
  return (
    <div className="grid grid-cols-3 items-center gap-4 p-4 rounded-lg">
      {/* Home Team (Left) */}
      <div className="flex flex-col md:items-center">
        <h2 className="text-xl font-bold">{game.homeTeam.teamName}</h2>
        <TeamLogos teamTricode={game.homeTeam.teamTricode} size={48} />
        <h2 className="text-2xl md:text-3xl font-bold mt-2 ">
          {game.homeTeam.score}
        </h2>
      </div>

      {/* Score Table (Center) */}
      <div className="flex justify-center items-center">
        {game.homeTeam.score > game.awayTeam.score && (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="7"
            height="12"
            viewBox="0 0 7 12"
            role="presentation"
          >
            <path
              fill="currentColor"
              fill-rule="nonzero"
              d="M.5 6l6 5.5V.5z"
            ></path>
          </svg>
        )}
        <table className="w-full max-w-55">
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
      <div className="flex flex-col md:items-center">
        <h2 className="text-xl font-bold">{game.awayTeam.teamName}</h2>
        <TeamLogos teamTricode={game.awayTeam.teamTricode} size={48} />
        <h2 className="text-2xl lg:text-3xl font-bold mt-2">{game.awayTeam.score}</h2>
      </div>
    </div>
  );
};

export default GameSummary;

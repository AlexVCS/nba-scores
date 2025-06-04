import {Team} from "@/helpers/helpers";

interface Game {
  homeTeam: Team;
  awayTeam: Team;
}

interface InactivePlayersProps {
  game: Game;
}

const getInactivePlayers = (team: Team) =>
  team.players.filter((player) => player.status === "INACTIVE");

const InactivePlayers: React.FC<InactivePlayersProps> = ({game}) => {
  const homeInactive = getInactivePlayers(game.homeTeam);
  const awayInactive = getInactivePlayers(game.awayTeam);

  if (homeInactive.length === 0 && awayInactive.length === 0) return null;

  return (
    <section className="p-2 text-sm dark:text-slate-50 text-neutral-950">
      <div className="border-solid border-b border-[#ebe9e7] mb-2">
        <h1 className="uppercase text-lg">Inactive Players</h1>
      </div>
      {homeInactive.length > 0 && (
        <p>
          {game.homeTeam.teamTricode}:{" "}
          {homeInactive.map((p) => p.name).join(", ")}
        </p>
      )}
      {awayInactive.length > 0 && (
        <p>
          {game.awayTeam.teamTricode}:{" "}
          {awayInactive.map((p) => p.name).join(", ")}
        </p>
      )}
    </section>
  );
};

export default InactivePlayers;

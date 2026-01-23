import {placeholderPlayerHeadshot} from "@/helpers/helpers.jsx";
import { Player } from "@/helpers/helpers.jsx";


interface PlayerHeadShotProps {
  player: Player
}

const PlayerHeadshot: React.FC<PlayerHeadShotProps> = ({player}) => {
const headshotUrl = `https://cdn.nba.com/headshots/nba/latest/260x190/${player.personId}.png`;

  return (
    <figure>
      <img
        src={headshotUrl}
        className="hidden md:block md:place-self-center"
        alt={`${player.nameI} headshot`}
        width="52"
        height="38"
        onError={(e) => {
          e.currentTarget.src = `${placeholderPlayerHeadshot}`;
        }}
      />
    </figure>
  );
};

export default PlayerHeadshot;

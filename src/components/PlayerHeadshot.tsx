import {placeholderPlayerHeadshot} from "@/helpers/helpers.jsx";
import {Player} from "@/routes/games/boxscore/Boxscore.jsx";

interface PlayerHeadShotProps {
  player: Player
}

const PlayerHeadshot: React.FC<PlayerHeadShotProps> = ({player}) => {
  return (
    <figure>
      <img
        src={`${
          import.meta.env.DEV
            ? import.meta.env.VITE_API_URL_DEV
            : import.meta.env.VITE_API_URL_PROD
        }/headshots/${player.personId}`}
        className="hidden md:block"
        alt={`${player.name} headshot`}
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

import * as NBAIcons from "react-nba-logos";
import {placeholderTeamLogo} from "@/helpers/helpers";

interface TeamLogoProps {
  teamName?: string;
  teamTricode: string;
  size: number;
}

type NBAIconsType = typeof NBAIcons;
type TeamCodeType = keyof NBAIconsType;

const TeamLogos = ({teamName, teamTricode, size}: TeamLogoProps) => {
  const TeamLogo = NBAIcons[teamTricode as TeamCodeType];
  return (
    <>
      <figure className="place-self-center">
        {TeamLogo ? <TeamLogo size={size} /> : placeholderTeamLogo}
      </figure>
      <figcaption className="sr-only">{teamName} logo</figcaption>
    </>
  );
};

export default TeamLogos;

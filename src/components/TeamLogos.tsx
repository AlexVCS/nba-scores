import { placeholderTeamLogoUrl } from "@/helpers/helpers";
import { HISTORICAL_TEAM_LOGOS } from "@/constants/historicalTeamLogos";

interface TeamLogoProps {
  teamName?: string;
  teamId: number;
  size: number;
  tricode?: string;
}

const TeamLogos = ({ teamName, teamId, size, tricode }: TeamLogoProps) => {
  const logoUrl = (tricode && HISTORICAL_TEAM_LOGOS[tricode])
    ?? `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;

  return (
    <>
      <figure className="flex items-center justify-center flex-shrink-0" style={{ width: size, height: size }}>
        {teamId ? (
          <img
            src={logoUrl}
            alt={`${teamName} logo`}
            width={size}
            height={size}
            style={{ objectFit: 'contain' }}
            onError={(e) => {
              e.currentTarget.src = placeholderTeamLogoUrl;
              e.currentTarget.onerror = null;
            }}
          />
        ) : (
          <img
            src={placeholderTeamLogoUrl}
            alt="Placeholder team logo"
            width={size}
            height={size}
            style={{ objectFit: 'contain' }}
          />
        )}
      </figure>
      <figcaption className="sr-only">{teamName} logo</figcaption>
    </>
  );
};

export default TeamLogos;
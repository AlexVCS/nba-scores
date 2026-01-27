import { placeholderTeamLogo } from "@/helpers/helpers";

interface TeamLogoProps {
  teamName?: string;
  teamId: number;
  size: number;
}

const TeamLogos = ({ teamName, teamId, size }: TeamLogoProps) => {
  const logoUrl = `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;

  return (
    <>
      <figure className="place-self-center flex items-center justify-center">
        {teamId ? (
          <img
            src={logoUrl}
            alt={`${teamName} logo`}
            width={size}
            height={size}
            style={{ objectFit: 'contain' }}
            onError={(e) => {
              e.currentTarget.src = `${placeholderTeamLogo}`;
              e.currentTarget.onerror = null;
            }}
          />
        ) : (
          <div style={{ width: size, height: size }}>
            {placeholderTeamLogo}
          </div>
        )}
      </figure>
      <figcaption className="sr-only">{teamName} logo</figcaption>
    </>
  );
};

export default TeamLogos;
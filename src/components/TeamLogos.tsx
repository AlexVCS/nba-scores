import { placeholderTeamLogo } from "@/helpers/helpers";

interface TeamLogoProps {
  teamName?: string;
  teamTricode: string;
  teamId: number | string;
  size: number;
}

const TeamLogos = ({ teamName, teamTricode, teamId, size }: TeamLogoProps) => {
  const logoUrl = `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;
  console.log(logoUrl)

  return (
    <>
      <figure className="place-self-center flex items-center justify-center">
        {teamId ? (
          <img
            src={logoUrl}
            alt={`${teamName || teamTricode} logo`}
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
      <figcaption className="sr-only">{teamName || teamTricode} logo</figcaption>
    </>
  );
};

export default TeamLogos;
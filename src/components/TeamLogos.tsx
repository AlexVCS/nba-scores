import { placeholderTeamLogoUrl } from "@/helpers/helpers";

interface TeamLogoProps {
  teamName?: string;
  teamId: number;
  size: number;
}

const TeamLogos = ({ teamName, teamId, size }: TeamLogoProps) => {
  const logoUrl = `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;

  return (
    <>
      <figure className="place-self-center flex items-center justify-center mb-2 p-2 dark:bg-white">
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
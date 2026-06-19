import { placeholderTeamLogoUrl } from "@/helpers/helpers";
import { HISTORICAL_TEAM_LOGOS } from "@/constants/historicalTeamLogos";

const add_contrast_to_logos = new Set<number | string>([
  1610612751, // BKN Nets
  1610612741, // CHI Bulls
  1610612757, // POR Trail Blazers
  1610612759, // SAS Spurs
  "GOS", // Golden State Warriors
  "SFW", // San Francisco Warriors
  "PHW", // Philadelphia Warriors
  "HUS", // Toronto Huskies
  "TCB", // Tri-Cities Blackhawks
  "KCK", // Kansas City Kings
]);

interface TeamLogoProps {
  teamName?: string;
  teamId: number;
  size: number;
  tricode?: string;
}

const TeamLogos = ({ teamName, teamId, size, tricode }: TeamLogoProps) => {
  const normalizedTricode = tricode?.trim().toUpperCase();
  const historicalLogoUrl = normalizedTricode
    ? HISTORICAL_TEAM_LOGOS[normalizedTricode]
    : undefined;
  const logoUrl = historicalLogoUrl
    ?? `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;
  const needsContrastTile = add_contrast_to_logos.has(teamId)
    || (normalizedTricode ? add_contrast_to_logos.has(normalizedTricode) : false);

  const logoImage = teamId ? (
    <img
      src={logoUrl}
      alt={`${teamName} logo`}
      width={size}
      height={size}
      className="h-full w-full"
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
      className="h-full w-full"
      style={{ objectFit: 'contain' }}
    />
  );

  return (
    <>
      <figure className="flex items-center justify-center flex-shrink-0" style={{ width: size, height: size }}>
        {needsContrastTile ? (
          <span className="flex h-full w-full items-center justify-center rounded bg-white p-0.5">
            {logoImage}
          </span>
        ) : (
          logoImage
        )}
      </figure>
      <figcaption className="sr-only">{teamName} logo</figcaption>
    </>
  );
};

export default TeamLogos;

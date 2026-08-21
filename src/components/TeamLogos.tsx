import { useContext } from "react";
import { placeholderTeamLogoUrl } from "@/helpers/helpers";
import { HISTORICAL_TEAM_LOGOS } from "@/constants/historicalTeamLogos";
import { ThemeContext } from "@/context/ThemeContext";

const HALO_CLASS = "team-logo--halo";

interface TeamLogoProps {
  teamName?: string;
  teamId: number;
  size: number;
  tricode?: string;
}

const TeamLogos = ({ teamName, teamId, size, tricode }: TeamLogoProps) => {
  // Tolerate rendering outside a ThemeProvider (e.g. isolated tests) by defaulting to light.
  const theme = useContext(ThemeContext)?.theme ?? "light";
  const normalizedTricode = tricode?.trim().toUpperCase();
  const historicalLogoUrl = normalizedTricode
    ? HISTORICAL_TEAM_LOGOS[normalizedTricode]
    : undefined;
  const cdnVariant = theme === "dark" ? "D" : "L";
  const logoUrl = historicalLogoUrl
    ?? `https://cdn.nba.com/logos/nba/${teamId}/global/${cdnVariant}/logo.svg`;
  const imageClassName = historicalLogoUrl
    ? `h-full w-full ${HALO_CLASS}`
    : "h-full w-full";

  const logoImage = teamId ? (
    <img
      src={logoUrl}
      alt={`${teamName} logo`}
      width={size}
      height={size}
      className={imageClassName}
      style={{ objectFit: 'contain' }}
      onError={(e) => {
        e.currentTarget.src = placeholderTeamLogoUrl;
        e.currentTarget.classList.add(HALO_CLASS);
        e.currentTarget.onerror = null;
      }}
    />
  ) : (
    <img
      src={placeholderTeamLogoUrl}
      alt="Placeholder team logo"
      width={size}
      height={size}
      className={`h-full w-full ${HALO_CLASS}`}
      style={{ objectFit: 'contain' }}
    />
  );

  return (
    <>
      <figure className="flex items-center justify-center flex-shrink-0" style={{ width: size, height: size }}>
        {logoImage}
      </figure>
      <figcaption className="sr-only">{teamName} logo</figcaption>
    </>
  );
};

export default TeamLogos;

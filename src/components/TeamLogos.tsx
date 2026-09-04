import { useContext, useState } from "react";
import { placeholderTeamLogoUrl } from "@/helpers/helpers";
import { HISTORICAL_TEAM_LOGOS, HISTORICAL_TEAM_LOGOS_BY_ID, HISTORICAL_TEAM_LOGO_ALIASES } from "@/constants/historicalTeamLogos";
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
  const historicalCode = normalizedTricode
    ? HISTORICAL_TEAM_LOGO_ALIASES[normalizedTricode] ?? normalizedTricode
    : undefined;
  const historicalLogoUrl = HISTORICAL_TEAM_LOGOS_BY_ID[teamId]
    ?? (historicalCode ? HISTORICAL_TEAM_LOGOS[historicalCode] : undefined);
  const cdnVariant = theme === "dark" ? "D" : "L";
  // Do not substitute a relocated franchise's modern identity for a historical logo.
  const candidates = historicalLogoUrl ? [historicalLogoUrl] : teamId ? [
    `https://cdn.nba.com/logos/nba/${teamId}/global/${cdnVariant}/logo.svg`,
    `https://cdn.nba.com/logos/nba/${teamId}/global/${cdnVariant === "D" ? "L" : "D"}/logo.svg`,
  ] : [];
  candidates.push(placeholderTeamLogoUrl);
  const requestKey = candidates.join("|");
  const [failure, setFailure] = useState({ requestKey: "", index: 0 });
  const index = failure.requestKey === requestKey ? failure.index : 0;
  const logoUrl = candidates[index];
  const isPlaceholder = logoUrl === placeholderTeamLogoUrl;
  const imageClassName = historicalLogoUrl || isPlaceholder
    ? `h-full w-full ${HALO_CLASS}`
    : "h-full w-full";

  const logoImage = (
    <img
      key={requestKey}
      src={logoUrl}
      alt={isPlaceholder ? "Placeholder team logo" : `${teamName} logo`}
      width={size}
      height={size}
      className={imageClassName}
      style={{ objectFit: 'contain' }}
      onError={isPlaceholder ? undefined : () => {
        setFailure({ requestKey, index: Math.min(index + 1, candidates.length - 1) });
      }}
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

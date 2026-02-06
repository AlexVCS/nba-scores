// NBA Team Colors - Primary and Secondary colors for each team
export const NBA_TEAM_COLORS: Record<number, { primary: string; secondary: string; accent: string }> = {
  // Atlanta Hawks
  1610612737: { primary: "#E03A3E", secondary: "#C1D32F", accent: "#26282A" },
  // Boston Celtics
  1610612738: { primary: "#007A33", secondary: "#BA9653", accent: "#FFFFFF" },
  // Brooklyn Nets
  1610612751: { primary: "#000000", secondary: "#FFFFFF", accent: "#777D84" },
  // Charlotte Hornets
  1610612766: { primary: "#1D1160", secondary: "#00788C", accent: "#A1A1A4" },
  // Chicago Bulls
  1610612741: { primary: "#CE1141", secondary: "#000000", accent: "#FFFFFF" },
  // Cleveland Cavaliers
  1610612739: { primary: "#860038", secondary: "#041E42", accent: "#FDBB30" },
  // Dallas Mavericks
  1610612742: { primary: "#00538C", secondary: "#002B5E", accent: "#B8C4CA" },
  // Denver Nuggets
  1610612743: { primary: "#0E2240", secondary: "#FEC524", accent: "#8B2131" },
  // Detroit Pistons
  1610612765: { primary: "#C8102E", secondary: "#1D42BA", accent: "#BEC0C2" },
  // Golden State Warriors
  1610612744: { primary: "#1D428A", secondary: "#FFC72C", accent: "#26282A" },
  // Houston Rockets
  1610612745: { primary: "#CE1141", secondary: "#000000", accent: "#C4CED4" },
  // Indiana Pacers
  1610612754: { primary: "#002D62", secondary: "#FDBB30", accent: "#BEC0C2" },
  // LA Clippers
  1610612746: { primary: "#C8102E", secondary: "#1D428A", accent: "#BEC0C2" },
  // Los Angeles Lakers
  1610612747: { primary: "#552583", secondary: "#FDB927", accent: "#000000" },
  // Memphis Grizzlies
  1610612763: { primary: "#5D76A9", secondary: "#12173F", accent: "#F5B112" },
  // Miami Heat
  1610612748: { primary: "#98002E", secondary: "#F9A01B", accent: "#000000" },
  // Milwaukee Bucks
  1610612749: { primary: "#00471B", secondary: "#EEE1C6", accent: "#0077C0" },
  // Minnesota Timberwolves
  1610612750: { primary: "#0C2340", secondary: "#236192", accent: "#9EA2A2" },
  // New Orleans Pelicans
  1610612740: { primary: "#0C2340", secondary: "#C8102E", accent: "#85714D" },
  // New York Knicks
  1610612752: { primary: "#006BB6", secondary: "#F58426", accent: "#BEC0C2" },
  // Oklahoma City Thunder
  1610612760: { primary: "#007AC1", secondary: "#EF3B24", accent: "#002D62" },
  // Orlando Magic
  1610612753: { primary: "#0077C0", secondary: "#C4CED4", accent: "#000000" },
  // Philadelphia 76ers
  1610612755: { primary: "#006BB6", secondary: "#ED174C", accent: "#002B5C" },
  // Phoenix Suns
  1610612756: { primary: "#1D1160", secondary: "#E56020", accent: "#000000" },
  // Portland Trail Blazers
  1610612757: { primary: "#E03A3E", secondary: "#000000", accent: "#FFFFFF" },
  // Sacramento Kings
  1610612758: { primary: "#5A2D81", secondary: "#63727A", accent: "#000000" },
  // San Antonio Spurs
  1610612759: { primary: "#C4CED4", secondary: "#000000", accent: "#FFFFFF" },
  // Toronto Raptors
  1610612761: { primary: "#CE1141", secondary: "#000000", accent: "#A1A1A4" },
  // Utah Jazz
  1610612762: { primary: "#002B5C", secondary: "#00471B", accent: "#F9A01B" },
  // Washington Wizards
  1610612764: { primary: "#002B5C", secondary: "#E31837", accent: "#C4CED4" },
};

export const getTeamColors = (teamId: number) => {
  return NBA_TEAM_COLORS[teamId] || { primary: "#1a1a2e", secondary: "#4a4a6a", accent: "#ffffff" };
};

export const getTeamGradient = (teamId: number, direction: string = "to right") => {
  const colors = getTeamColors(teamId);
  return `linear-gradient(${direction}, ${colors.primary}, ${colors.secondary})`;
};

export const getTeamGlow = (teamId: number, intensity: number = 0.5) => {
  const colors = getTeamColors(teamId);
  return `0 0 ${20 * intensity}px ${colors.primary}, 0 0 ${40 * intensity}px ${colors.secondary}`;
};

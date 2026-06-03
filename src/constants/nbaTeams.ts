// NBA team IDs mapped to conferences
// Eastern Conference teams (15 teams)
export const EASTERN_CONFERENCE_TEAMS = [
  1610612738, // Boston Celtics
  1610612751, // Brooklyn Nets
  1610612752, // New York Knicks
  1610612755, // Philadelphia 76ers
  1610612761, // Toronto Raptors
  1610612741, // Chicago Bulls
  1610612739, // Cleveland Cavaliers
  1610612765, // Detroit Pistons
  1610612754, // Indiana Pacers
  1610612749, // Milwaukee Bucks
  1610612737, // Atlanta Hawks
  1610612766, // Charlotte Hornets
  1610612748, // Miami Heat
  1610612753, // Orlando Magic
  1610612764, // Washington Wizards
];

// Western Conference teams (15 teams)
export const WESTERN_CONFERENCE_TEAMS = [
  // Northwest
  1610612743, // Denver Nuggets
  1610612750, // Minnesota Timberwolves
  1610612760, // Oklahoma City Thunder
  1610612757, // Portland Trail Blazers
  1610612762, // Utah Jazz
  // Pacific
  1610612744, // Golden State Warriors
  1610612746, // LA Clippers
  1610612747, // Los Angeles Lakers
  1610612756, // Phoenix Suns
  1610612758, // Sacramento Kings
  // Southwest
  1610612742, // Dallas Mavericks
  1610612745, // Houston Rockets
  1610612763, // Memphis Grizzlies
  1610612740, // New Orleans Pelicans
  1610612759, // San Antonio Spurs
];

// Historical teams (relocated/renamed franchises)
export const HISTORICAL_EASTERN_TEAMS = [
  1610612766, // Charlotte Bobcats (now Hornets)
  1610612752, // New Jersey Nets (now Brooklyn Nets)
];

export const HISTORICAL_WESTERN_TEAMS = [
  1610612760, // Seattle SuperSonics (now Oklahoma City Thunder)
  1610612740, // New Orleans/Oklahoma City Hornets (now Pelicans)
  1610612763, // Vancouver Grizzlies (now Memphis Grizzlies)
];

/**
 * Determines which conference a team belongs to based on their team ID
 */
export function getTeamConference(teamId: number): 'East' | 'West' | null {
  if (EASTERN_CONFERENCE_TEAMS.includes(teamId) || HISTORICAL_EASTERN_TEAMS.includes(teamId)) {
    return 'East';
  }
  if (WESTERN_CONFERENCE_TEAMS.includes(teamId) || HISTORICAL_WESTERN_TEAMS.includes(teamId)) {
    return 'West';
  }
  return null;
}

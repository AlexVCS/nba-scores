import conferences from './nbaConferences.json';

export const EASTERN_CONFERENCE_TEAMS: number[] = conferences.east;
export const WESTERN_CONFERENCE_TEAMS: number[] = conferences.west;

export const EASTERN_CONFERENCE_SET = new Set(EASTERN_CONFERENCE_TEAMS);
export const WESTERN_CONFERENCE_SET = new Set(WESTERN_CONFERENCE_TEAMS);

/**
 * Determines which conference a team belongs to based on their team ID
 */
export function getTeamConference(teamId: number): 'East' | 'West' | null {
  if (EASTERN_CONFERENCE_SET.has(teamId)) {
    return 'East';
  }
  if (WESTERN_CONFERENCE_SET.has(teamId)) {
    return 'West';
  }
  return null;
}

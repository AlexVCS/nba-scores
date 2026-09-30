import type {
  AskDetectedType,
  AskInterpretationField,
  AskPostseasonFinish,
  AskStat,
  Conference,
  PlayoffRound,
  Season,
} from "@/services/ask/types";

export const DETECTED_TYPE_LABELS: Record<AskDetectedType, string> = {
  games: "Games",
  player_stat: "Player stat",
  team_stat: "Team stat",
  stat_leaders: "Stat leaders",
  series: "Series",
  postseason: "Postseason",
  season_stats: "Season stats",
  team_records: "Records / standings",
};

export const FIELD_LABELS: Record<AskInterpretationField, string> = {
  player: "Player",
  team: "Team",
  teams: "Teams",
  game: "Game",
  date: "Date",
  dates: "Dates",
  stat: "Stat",
  season: "Season",
  round: "Round",
  series: "Series",
  game_number: "Game",
  location: "Location",
  aggregation: "Measure",
  season_type: "Season type",
  standings_scope: "Conference",
};

export const STAT_LABELS: Record<AskStat, string> = {
  stat_line: "Stat line",
  points: "Points",
  rebounds: "Rebounds",
  offensive_rebounds: "Offensive rebounds",
  defensive_rebounds: "Defensive rebounds",
  assists: "Assists",
  steals: "Steals",
  blocks: "Blocks",
  turnovers: "Turnovers",
  fouls: "Fouls",
  minutes: "Minutes",
  field_goals: "Field goals",
  three_pointers: "3-pointers",
  free_throws: "Free throws",
  field_goal_percentage: "FG%",
  three_point_percentage: "3P%",
  free_throw_percentage: "FT%",
  plus_minus: "Plus/minus",
};

export const FINISH_LABELS: Record<AskPostseasonFinish, string> = {
  champion: "Won the NBA Finals",
  lost_finals: "Lost in the NBA Finals",
  lost_conference_finals: "Lost in the conference finals",
  lost_conference_semifinals: "Lost in the conference semifinals",
  lost_first_round: "Lost in the first round",
  lost_play_in: "Lost in the play-in",
  did_not_qualify: "Did not qualify",
  in_progress: "Still playing",
};

export function roundLabel(round: PlayoffRound, conference: Conference | null = null): string {
  const conf = conference === "east" ? "East" : conference === "west" ? "West" : "";
  switch (round) {
    case "first_round":
      return conf ? `${conf} First Round` : "First Round";
    case "conference_semifinals":
      return conf ? `${conf} Semifinals` : "Conference Semifinals";
    case "conference_finals":
      return conf ? `${conf} Finals` : "Conference Finals";
    case "finals":
      return "NBA Finals";
  }
}

/** "2025-26" → 2026, the year the playoffs are played. */
export function playoffYear(season: Season): number {
  return Number(season.slice(0, 4)) + 1;
}

export function formatAskDate(date: string, options: Intl.DateTimeFormatOptions = {weekday: "short", month: "short", day: "numeric", year: "numeric"}): string {
  const parsed = new Date(`${date}T12:00:00`);
  return Number.isNaN(parsed.getTime()) ? date : parsed.toLocaleDateString("en-US", options);
}

/** Fetch timestamps use the same Eastern calendar as Ask's interpretation. */
export function formatAskTimestamp(timestamp: string): string {
  const parsed = new Date(timestamp);
  return Number.isNaN(parsed.getTime()) ? timestamp : parsed.toLocaleDateString("en-US", {
    timeZone: "America/New_York", weekday: "short", month: "short", day: "numeric", year: "numeric",
  });
}

export function formatAskRange(start: string, end: string): string {
  return start === end ? formatAskDate(start) : `${formatAskDate(start)} – ${formatAskDate(end)}`;
}

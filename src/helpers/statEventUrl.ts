// Links from boxscore counting stats to NBA.com's event pages (issue #187).
// The backend decides which measures are linkable for a game; the frontend only
// builds URLs from the `statEvents` block it returns.

export type StatEventMeasure =
  | "FGM" | "FGA" | "FG3M" | "FG3A"
  | "OREB" | "DREB" | "REB" | "AST" | "STL" | "BLK" | "TOV";

// NBA.com's event-page `flag`, the only values its box score emits.
export type StatEventFlag = 1 | 2 | 3;

export interface StatEvents {
  season: string;
  seasonType: string;
  endRange: number;
  // Only linkable measures are present; each value is NBA.com's `flag`.
  measures: Partial<Record<StatEventMeasure, StatEventFlag>>;
}

export const STAT_EVENT_MEASURE_NAMES: Record<StatEventMeasure, string> = {
  FGM: "field goals made",
  FGA: "field goals attempted",
  FG3M: "three-pointers made",
  FG3A: "three-pointers attempted",
  OREB: "offensive rebounds",
  DREB: "defensive rebounds",
  REB: "rebounds",
  AST: "assists",
  STL: "steals",
  BLK: "blocks",
  TOV: "turnovers",
};

const STAT_EVENTS_BASE = "https://www.nba.com/stats/events/";

interface StatEventUrlOptions {
  statEvents: StatEvents;
  gameId: string;
  teamId: number;
  // Omitted for team-total links.
  personId?: number;
  measure: StatEventMeasure;
  flag: StatEventFlag;
}

// NBA.com serializes the query by hand: keys sorted, values passed through
// encodeURI, empty parameters kept. URLSearchParams would turn spaces into "+".
export const buildStatEventUrl = ({statEvents, gameId, teamId, personId, measure, flag}: StatEventUrlOptions) => {
  const params: Record<string, string | number> = {
    CFID: "",
    CFPARAMS: "",
    ContextMeasure: measure,
    EndPeriod: 0,
    EndRange: statEvents.endRange,
    GameID: gameId,
    RangeType: 0,
    Season: statEvents.season,
    SeasonType: statEvents.seasonType,
    StartPeriod: 0,
    StartRange: 0,
    TeamID: teamId,
    flag,
    sct: "plot",
    section: "game",
  };
  if (personId !== undefined) params.PlayerID = personId;
  const query = Object.keys(params)
    .sort()
    .map((key) => `${encodeURI(key)}=${encodeURI(String(params[key]))}`)
    .join("&");
  return `${STAT_EVENTS_BASE}?${query}`;
};

interface StatEventLinkOptions extends Omit<StatEventUrlOptions, "flag" | "statEvents"> {
  statEvents: StatEvents | null | undefined;
  value: number;
}

// The URL for a displayed stat, or null when it stays plain text: no statEvents
// for the game, a measure NBA.com does not link, or a zero value.
export const statEventUrl = ({statEvents, value, measure, ...rest}: StatEventLinkOptions) => {
  const flag = statEvents?.measures[measure];
  if (!statEvents || !flag || !(value > 0)) return null;
  return buildStatEventUrl({statEvents, measure, flag, ...rest});
};

const possessive = (name: string) => (name.endsWith("s") ? `${name}'` : `${name}'s`);

export const statEventLabel = (subject: string, measure: StatEventMeasure) =>
  `View ${possessive(subject)} ${STAT_EVENT_MEASURE_NAMES[measure]} on NBA.com, opens in new tab`;

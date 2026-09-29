// Ask HTTP contract. Mirrors server/ask/models/response.py (source of truth).
// Frozen: change only through a coordinated contract PR (docs/ask-contract.md).
//
// Keys are snake_case except the embedded scoreboard `game` payload, which is
// the unchanged GameData shape used by GameCard.
//
// Spoilers: `Guarded<T>` values and anything with `spoiler: true` must be
// omitted from the DOM and accessibility text while results are hidden.

import type {GameData} from "@/helpers/helpers";

export const ASK_SCHEMA_VERSION = "1";
export const ASK_MAX_QUESTION_LENGTH = 300;
export const ASK_MAX_CLARIFICATION_OPTIONS = 9;

export type IsoDate = string; // "2026-02-08" (America/New_York calendar date)
export type IsoDateTime = string; // "2026-02-09T10:15:00-05:00"
export type Season = string; // "2023-24"

export type AskIntent = "game_search" | "boxscore_stat" | "playoff_series" | "postseason_summary";
export type AskOutcome =
  | "answer"
  | "needs_clarification"
  | "unsupported"
  | "not_found"
  | "unavailable"
  | "budget_exhausted";
export type AskDetectedType = "games" | "player_stat" | "team_stat" | "stat_leaders" | "series" | "postseason";
export type AskStatScope = "player" | "team" | "leaders";
export type AskStatKey =
  | "points"
  | "rebounds"
  | "offensive_rebounds"
  | "defensive_rebounds"
  | "assists"
  | "steals"
  | "blocks"
  | "turnovers"
  | "fouls"
  | "minutes"
  | "field_goals"
  | "three_pointers"
  | "free_throws"
  | "field_goal_percentage"
  | "three_point_percentage"
  | "free_throw_percentage"
  | "plus_minus";
export type AskStat = "stat_line" | AskStatKey;
export type AskAggregation = "total" | "per_game";
export type PlayoffRound = "first_round" | "conference_semifinals" | "conference_finals" | "finals";
export type Conference = "east" | "west";
export type AskAppRoute = "scores" | "boxscore" | "playoffs" | "series" | "other";
export type AskAdapterName = "jev" | "openai_responses";
export type AskUnsupportedReason =
  | "career_stats"
  | "season_stats"
  | "season_leaders"
  | "historical_comparison"
  | "prediction"
  | "follow_up"
  | "regular_season_record"
  | "standings"
  | "reference_question"
  | "multi_game_average"
  | "unsupported_leader_stat"
  | "not_basketball"
  | "other";

export interface Guarded<T> {
  value: T;
  spoiler: boolean;
}

export interface AskTeamRef {
  team_id: number;
  tricode: string;
  name: string;
}

export interface AskPlayerRef {
  player_id: number;
  name: string;
}

export interface AskDateRange {
  start: IsoDate;
  end: IsoDate;
}

// ---------------------------------------------------------------- request

export interface AskClientContext {
  route?: AskAppRoute | null;
  view_date?: IsoDate | null;
  game_id?: string | null;
  playoff_season?: Season | null;
}

export interface AskQuery {
  question: string;
  context?: AskClientContext | null;
  /**
   * Opaque token from a ClarificationOption. Zero model calls: the reply is the
   * answer, or the next clarification when fields remain (a token can hold a
   * partial resolution). Expired or invalid tokens are ignored and `question`
   * is handled as a new question.
   */
  resolution?: string | null;
}

// ---------------------------------------------------------------- shared

export type AskLinkKind =
  | "boxscore"
  | "scores_date"
  | "playoff_series"
  | "playoff_bracket"
  | "nba_game"
  | "nba_stat_event";

/** The only URL-bearing type: every link in a response uses it. */
export interface AskVerifiedLink {
  kind: AskLinkKind;
  label: string;
  /** Internal hrefs are design-agnostic app paths; prefix the active design. */
  href: string;
  external: boolean;
  spoiler: boolean;
}

export interface AskSourceMetadata {
  name: "nba_live" | "nba_stats" | "nba_schedule" | "basketball_reference" | "app_cache";
  label: string;
  fetched_at: IsoDateTime | null;
  complete: boolean;
}

export interface AskInterpreterInfo {
  model_called: boolean;
  cache_hit: boolean;
  adapter: AskAdapterName | null;
  model: string | null;
  fallback_used: boolean;
}

// ---------------------------------------------------------------- interpretation

export type AskInterpretationField =
  | "player"
  | "team"
  | "teams"
  | "game"
  | "date"
  | "dates"
  | "stat"
  | "season"
  | "round"
  | "series"
  | "game_number";

export interface AskInterpretationItem {
  field: AskInterpretationField;
  value: string;
  detail: string | null;
  expression: string | null;
  origin: "question" | "inferred" | "context";
  status: "resolved" | "ambiguous";
  match_count: number | null;
  team_id: number | null;
  player_id: number | null;
  spoiler: boolean;
}

export interface AskInterpretation {
  intent: AskIntent | null;
  detected_type: AskDetectedType | null;
  items: AskInterpretationItem[];
  reference_time: IsoDateTime;
  timezone: "America/New_York";
  dates: AskDateRange | null;
  season: Season | null;
}

// ---------------------------------------------------------------- results

export interface AskGameSpoilers {
  score: boolean;
  status_text: boolean;
  series_text: boolean;
  /** gameLabel, gameSubLabel, seriesGameNumber, ifNecessary ("Game 7", round names). */
  labels: boolean;
}

export interface AskGameResultItem {
  date: IsoDate;
  /** Unchanged scoreboard payload; may carry extra scoreboard keys. */
  game: GameData;
  spoilers: AskGameSpoilers;
  links: AskVerifiedLink[];
  /** The game's existence reveals a result (e.g. a possible Game 5-7): omit the whole item while hidden. */
  spoiler: boolean;
}

export interface AskGameDay {
  date: IsoDate;
  games: AskGameResultItem[];
}

export interface AskGamesResult {
  kind: "games";
  dates: AskDateRange;
  teams: AskTeamRef[];
  days: AskGameDay[];
  total_games: Guarded<number>;
  /** Neutral copy to show while hidden when some games are spoilers. */
  hidden_note: string | null;
}

export interface AskStatValue {
  stat: AskStatKey;
  value: number | null;
  display: string;
  made: number | null;
  attempted: number | null;
}

export interface AskFinalScore {
  away: number;
  home: number;
  periods: number;
}

export interface AskGameContext {
  game_id: string;
  date: IsoDate;
  away: Guarded<AskTeamRef>;
  home: Guarded<AskTeamRef>;
  season: Season;
  season_type: "regular_season" | "playoffs" | "play_in" | "preseason" | "all_star" | "nba_cup_final";
  round: PlayoffRound | null;
  game_number: number | null;
  final_score: Guarded<AskFinalScore | null>;
}

export interface AskPlayerStatLine {
  player: AskPlayerRef;
  team: AskTeamRef;
  status: "played" | "did_not_play" | "inactive";
  values: Guarded<AskStatValue>[];
}

export interface AskTeamStatLine {
  team: AskTeamRef;
  values: Guarded<AskStatValue>[];
}

export interface AskLeaderRow {
  /** Ties share a rank. */
  rank: number;
  player: AskPlayerRef;
  team: AskTeamRef;
  value: AskStatValue;
}

export interface AskBoxscoreStatResult {
  kind: "boxscore_stat";
  scope: AskStatScope;
  stat: AskStat;
  aggregation: AskAggregation;
  game: AskGameContext;
  player_line: AskPlayerStatLine | null;
  team_lines: AskTeamStatLine[];
  /** Leaders scope only; guarded as a whole (ranks and length reveal ties). */
  leaders: Guarded<AskLeaderRow[]> | null;
}

export type AskSeriesStatus = "not_started" | "in_progress" | "complete";

export interface AskSeriesTeamRow {
  team: Guarded<AskTeamRef>;
  seed: Guarded<number | null>;
  wins: Guarded<number>;
  won_series: Guarded<boolean | null>;
}

export interface AskPlayoffSeriesResult {
  kind: "playoff_series";
  season: Season;
  round: PlayoffRound;
  conference: Conference | null;
  teams: [AskSeriesTeamRow, AskSeriesTeamRow];
  status: Guarded<AskSeriesStatus>;
  games_played: Guarded<number>;
  summary: Guarded<string>;
  games: Guarded<AskGameResultItem[]>;
}

export interface AskWinLoss {
  wins: number;
  losses: number;
}

export type AskPostseasonFinish =
  | "champion"
  | "lost_finals"
  | "lost_conference_finals"
  | "lost_conference_semifinals"
  | "lost_first_round"
  | "lost_play_in"
  | "did_not_qualify"
  | "in_progress";

export interface AskPostseasonRoundRow {
  round: PlayoffRound;
  conference: Conference | null;
  opponent: AskTeamRef;
  team_wins: number;
  opponent_wins: number;
  won: boolean | null;
  series_link: AskVerifiedLink | null;
}

export interface AskSeriesParticipant {
  team: AskTeamRef;
  wins: number;
}

export interface AskPostseasonSeriesRow {
  round: PlayoffRound;
  conference: Conference | null;
  teams: [AskSeriesParticipant, AskSeriesParticipant];
  status: AskSeriesStatus;
  /** Set iff status is "complete". */
  winner_team_id: number | null;
}

export interface AskPostseasonSummaryResult {
  kind: "postseason_summary";
  season: Season;
  team: AskTeamRef | null;
  finish: Guarded<AskPostseasonFinish | null>;
  record: Guarded<AskWinLoss | null>;
  series_won: Guarded<number | null>;
  rounds: Guarded<AskPostseasonRoundRow[]>;
  champion: Guarded<AskTeamRef | null>;
  runner_up: Guarded<AskTeamRef | null>;
  series: Guarded<AskPostseasonSeriesRow[]>;
}

export type AskResult =
  | AskGamesResult
  | AskBoxscoreStatResult
  | AskPlayoffSeriesResult
  | AskPostseasonSummaryResult;

// ---------------------------------------------------------------- clarification, notices

export type AskClarifyField =
  | "intent"
  | "stat_scope"
  | "stat"
  | "player"
  | "teams"
  | "date"
  | "season"
  | "round"
  | "game_number";
export type AskClarifyReason = "ambiguous" | "missing" | "no_matching_candidate" | "year_required" | "range_too_long";

export interface AskClarificationOption {
  id: string;
  label: string;
  sublabel: string | null;
  detail: string | null;
  team: AskTeamRef | null;
  player_id: number | null;
  /** Standalone rewritten question, for the input and recent history. */
  question: string;
  /** Send back as AskQuery.resolution; may lead to another clarification. */
  resolution: string;
  spoiler: boolean;
}

export interface AskClarification {
  field: AskClarifyField;
  reason: AskClarifyReason;
  prompt: string;
  detail: string | null;
  options: AskClarificationOption[];
  hint: string | null;
}

export type AskNoticeCode =
  | "unsupported"
  | "no_games"
  | "no_record"
  | "player_did_not_play"
  | "service_unavailable"
  | "interpreter_unavailable"
  | "budget_exhausted"
  | "rate_limited";

export interface AskNotice {
  code: AskNoticeCode;
  title: string;
  message: string;
  retryable: boolean;
  retry_after_seconds: number | null;
  unsupported_reason: AskUnsupportedReason | null;
  diagnostics_recorded: boolean;
}

/**
 * Neutral hidden-state copy for questions whose every outcome reveals a result.
 * While hidden, render only this, non-spoiler interpretation items, and a reveal
 * control; do not render or branch on outcome, result, notice, links, or suggestions.
 */
export interface AskSpoilerGate {
  title: string;
  message: string;
}

export type AskSuggestionCategory = "games" | "stats" | "series" | "postseason";

export interface AskSuggestion {
  question: string;
  category: AskSuggestionCategory;
  /** Drop while results are hidden. */
  spoiler: boolean;
}

// ---------------------------------------------------------------- response

export interface AskResponse {
  schema_version: typeof ASK_SCHEMA_VERSION;
  request_id: string;
  outcome: AskOutcome;
  question: string;
  interpretation: AskInterpretation | null;
  result: AskResult | null;
  clarification: AskClarification | null;
  notice: AskNotice | null;
  spoiler_gate: AskSpoilerGate | null;
  links: AskVerifiedLink[];
  suggestions: AskSuggestion[];
  sources: AskSourceMetadata[];
  interpreter: AskInterpreterInfo;
}

// ---------------------------------------------------------------- GET /ask/suggest

export interface AskSuggestGame {
  game_id: string;
  date: IsoDate;
  away: AskTeamRef;
  home: AskTeamRef;
  label: string;
  link: AskVerifiedLink;
}

export interface AskSuggestEntity {
  kind: "player" | "team";
  label: string;
  player_id: number | null;
  team: AskTeamRef | null;
}

export interface AskSuggestResponse {
  query: string;
  games: AskSuggestGame[];
  entities: AskSuggestEntity[];
  questions: AskSuggestion[];
}

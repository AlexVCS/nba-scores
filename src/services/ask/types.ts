// Ask HTTP contract. Mirrors server/ask/models/response.py (source of truth).
// Frozen: change only through a coordinated contract PR (docs/ask-contract.md).
//
// Keys are snake_case except the embedded scoreboard `game` payload, which is
// the unchanged GameData shape used by GameCard.
//
// Spoilers (ADR 0006): asking is consent, so results and notices are shown as
// soon as they arrive. `spoiler: true` marks what the user did not ask for
// (interpretation chips beside a clarification, clarification options, links,
// suggestions); omit those from the DOM and accessibility text while results
// are hidden.

import type {GameData} from "@/helpers/helpers";

export const ASK_SCHEMA_VERSION = "1";
export const ASK_MAX_QUESTION_LENGTH = 300;
export const ASK_MAX_CLARIFICATION_OPTIONS = 9;

export type IsoDate = string; // "2026-02-08" (America/New_York calendar date)
export type IsoDateTime = string; // "2026-02-09T10:15:00-05:00"
export type Season = string; // "2023-24"

export type AskIntent = "game_search" | "boxscore_stat" | "playoff_series" | "postseason_summary" | "player_season_stats" | "team_records" | "season_leaders";
export type AskOutcome =
  | "answer"
  | "needs_clarification"
  | "unsupported"
  | "not_found"
  | "unavailable"
  | "budget_exhausted";
export type AskDetectedType = "games" | "player_stat" | "team_stat" | "stat_leaders" | "series" | "postseason" | "season_stats" | "team_records" | "season_leaders";
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
export type AskAdapterName = "laya" | "jev" | "openai_responses" | "cascade";
export type AskUnsupportedReason =
  | "season_stats" // Legacy responses only.
  | "regular_season_record"
  | "standings"
  | "career_stats"
  | "season_leaders" // Legacy responses only since stage 3.
  | "historical_comparison"
  | "prediction"
  | "follow_up"
  | "reference_question"
  | "multi_game_average"
  | "unsupported_leader_stat"
  | "not_basketball"
  | "other";

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
  | "nba_stat_event"
  | "source";

/** The only URL-bearing type: every link in a response uses it. */
export interface AskVerifiedLink {
  kind: AskLinkKind;
  label: string;
  /** Internal hrefs are design-agnostic app paths; prefix the active design. */
  href: string;
  external: boolean;
  /** Would reveal a result the user did not ask for; omit while results are hidden. */
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
  field_tiers?: Record<string, string>;
  /** Development servers only (`ASK_DEV=1`); absent in production. */
  field_decisions?: AskFieldDecision[];
}

export interface AskTierRead {
  tier: string;
  status: "selected" | "absent" | "ambiguous" | "no_matching_candidate" | "unsupported";
  confidence: number | null;
  action: "accepted" | "escalated" | "vetoed" | "unused";
}

/** Per-field cascade diagnostics (ADRs 0002, 0009, 0010). Dev details only; carries no values. */
export interface AskFieldDecision {
  field: string;
  /** "lookup", "laya", "jev", "luna", or "veto"; null when no tier decided the field. */
  decided_by: string | null;
  confidence: number | null;
  outcome: "accepted" | "escalated" | "vetoed" | "undecided";
  reads: AskTierRead[];
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
  | "game_number"
  | "location"
  | "aggregation"
  | "season_type"
  | "standings_scope";

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

export interface AskGameResultItem {
  date: IsoDate;
  /** Unchanged scoreboard payload; may carry extra scoreboard keys. */
  game: GameData;
  links: AskVerifiedLink[];
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
  total_games: number;
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
  away: AskTeamRef;
  home: AskTeamRef;
  season: Season;
  season_type: "regular_season" | "playoffs" | "play_in" | "preseason" | "all_star" | "nba_cup_final";
  round: PlayoffRound | null;
  game_number: number | null;
  /** Null for games not finished. */
  final_score: AskFinalScore | null;
}

export interface AskPlayerStatLine {
  player: AskPlayerRef;
  team: AskTeamRef;
  status: "played" | "did_not_play" | "inactive";
  values: AskStatValue[];
}

export interface AskTeamStatLine {
  team: AskTeamRef;
  values: AskStatValue[];
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
  /** Leaders scope only. */
  leaders: AskLeaderRow[] | null;
}

export type AskSeriesStatus = "not_started" | "in_progress" | "complete";

export interface AskSeriesTeamRow {
  team: AskTeamRef;
  seed: number | null;
  wins: number;
  won_series: boolean | null;
}

export interface AskPlayoffSeriesResult {
  kind: "playoff_series";
  season: Season;
  round: PlayoffRound;
  conference: Conference | null;
  teams: [AskSeriesTeamRow, AskSeriesTeamRow];
  status: AskSeriesStatus;
  games_played: number;
  summary: string;
  games: AskGameResultItem[];
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
  finish: AskPostseasonFinish | null;
  record: AskWinLoss | null;
  series_won: number | null;
  rounds: AskPostseasonRoundRow[];
  champion: AskTeamRef | null;
  runner_up: AskTeamRef | null;
  series: AskPostseasonSeriesRow[];
}

export interface AskPlayerSeasonStatsResult {
  kind: "player_season_stats";
  player: AskPlayerRef;
  season: Season;
  season_type: "regular_season" | "playoffs";
  aggregation: AskAggregation;
  team: AskTeamRef | null;
  games_played: number;
  values: AskStatValue[];
  coverage_note: string | null;
  as_of: IsoDateTime;
}

export interface AskTeamRecordRow {
  team: AskTeamRef;
  wins: number;
  losses: number;
  win_percentage: number;
  conference: Conference | null;
  conference_rank: number | null;
}

export interface AskTeamRecordsResult {
  kind: "team_records";
  season: Season;
  team: AskTeamRef | null;
  standings_scope: "league" | "east" | "west";
  rows: AskTeamRecordRow[];
  as_of: IsoDateTime;
}

export interface AskSeasonLeaderRow {
  /** Competition rank on unrounded values: tied players share a rank. */
  rank: number;
  player: AskPlayerRef;
  /** Null when the player had several teams, or the franchise is outside the catalog. */
  team: AskTeamRef | null;
  multiple_teams: boolean;
  games_played: number;
  value: AskStatValue;
}

export interface AskSeasonLeadersResult {
  kind: "season_leaders";
  season: Season;
  season_type: "regular_season" | "playoffs";
  stat: AskStatKey;
  aggregation: AskAggregation;
  /** Requested top N; every player ranked N or better is listed, so ties can add rows. */
  limit: number;
  qualification: "all_players" | "source_qualified";
  qualification_note: string;
  rows: AskSeasonLeaderRow[];
  /** A whole tie group left out because it would pass the 50-row cap. */
  omitted_tie: {rank: number; count: number} | null;
  coverage_note: string | null;
  as_of: IsoDateTime;
}

export type AskResult =
  | AskGamesResult
  | AskBoxscoreStatResult
  | AskPlayoffSeriesResult
  | AskPostseasonSummaryResult
  | AskPlayerSeasonStatsResult
  | AskTeamRecordsResult
  | AskSeasonLeadersResult;

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
  | "game_number"
  | "location"
  | "aggregation"
  | "season_type"
  | "standings_scope";
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
  /** Reveals a result; options are not answers, so omit while results are hidden unless the user shows them. */
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

export type AskSuggestionCategory = "games" | "stats" | "series" | "postseason";

export interface AskSuggestion {
  question: string;
  category: AskSuggestionCategory;
  /** Reveals a result; suggestions are never requested, so drop while results are hidden. */
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

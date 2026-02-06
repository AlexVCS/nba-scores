import {useQuery} from "@tanstack/react-query";
import {useParams, Link} from "react-router-dom";
import {useTheme} from "@/hooks/useTheme";
import DarkModeToggle from "@/components/DarkModeToggle";
import {getBoxScores, getGameSummary} from "@/services/nbaService";
import {formatMinutesPlayed, placeholderTeamLogoUrl} from "@/helpers/helpers";
import type {Player, Team} from "@/helpers/helpers";
import {getTeamColors} from "../shared/teamColors";
import "./design5.css";

const A5Boxscore = () => {
  const {theme} = useTheme();
  const {gameId = ""} = useParams();

  const boxscoreQuery = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => getBoxScores(gameId),
  });

  const gameSummaryQuery = useQuery({
    queryKey: ["gameSummary", gameId],
    queryFn: () => getGameSummary(gameId),
  });

  if (boxscoreQuery.isLoading || gameSummaryQuery.isLoading) {
    return (
      <div className={`analytics-container ${theme}`}>
        <div className="analytics-loading">Loading boxscore data...</div>
      </div>
    );
  }

  if (boxscoreQuery.isError || !boxscoreQuery.data) {
    return (
      <div className={`analytics-container ${theme}`}>
        <div className="analytics-no-games">Error loading boxscore</div>
      </div>
    );
  }

  const {game} = boxscoreQuery.data;
  const summary = gameSummaryQuery.data;

  const getLogoUrl = (teamId: number) => `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;

  const homeWinning = summary && Number(summary.homeTeam.score) > Number(summary.awayTeam.score);
  const awayWinning = summary && Number(summary.awayTeam.score) > Number(summary.homeTeam.score);

  const homeColors = summary ? getTeamColors(summary.homeTeam.teamId) : {primary: '#14b8a6'};
  const awayColors = summary ? getTeamColors(summary.awayTeam.teamId) : {primary: '#6366f1'};

  return (
    <div className={`analytics-container ${theme}`}>
      <header className="analytics-header">
        <div className="analytics-header-left">
          <Link to="/5" className="analytics-back-link">
            ← Back to Scores
          </Link>
        </div>
        <DarkModeToggle />
      </header>

      <div className="analytics-boxscore-container">
        {/* Game Summary */}
        {summary && (
          <div 
            className="analytics-summary-panel"
            style={{
              '--home-color': homeColors.primary,
              '--away-color': awayColors.primary,
            } as React.CSSProperties}
          >
            <div className="analytics-summary-header" />
            <div className="analytics-summary-content">
              <div className="analytics-summary-grid">
                {/* Home Team */}
                <div className="analytics-summary-team">
                  <img
                    src={getLogoUrl(summary.homeTeam.teamId)}
                    alt={summary.homeTeam.teamName}
                    className="analytics-summary-logo"
                    onError={(e) => {
                      e.currentTarget.src = placeholderTeamLogoUrl;
                    }}
                  />
                  <div className="analytics-summary-team-info">
                    <div className="analytics-summary-name">{summary.homeTeam.teamName}</div>
                    <div className={`analytics-summary-score ${homeWinning ? "winner" : ""}`}>
                      {summary.homeTeam.score}
                    </div>
                  </div>
                </div>

                {/* Quarter Table */}
                <div className="analytics-quarter-wrapper">
                  <table className="analytics-quarter-table">
                    <thead>
                      <tr>
                        <th></th>
                        <th>Q1</th>
                        <th>Q2</th>
                        <th>Q3</th>
                        <th>Q4</th>
                        {summary.homeTeam.periods.slice(4).map((p: {period: number}) => (
                          <th key={`ot-${p.period}`}>OT{p.period - 4}</th>
                        ))}
                        <th>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>{summary.homeTeam.teamTricode}</td>
                        {summary.homeTeam.periods.map((period: {period: number; score: string}) => (
                          <td key={period.period}>{period.score}</td>
                        ))}
                        <td className="total">{summary.homeTeam.score}</td>
                      </tr>
                      <tr>
                        <td>{summary.awayTeam.teamTricode}</td>
                        {summary.awayTeam.periods.map((period: {period: number; score: string}) => (
                          <td key={period.period}>{period.score}</td>
                        ))}
                        <td className="total">{summary.awayTeam.score}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Away Team */}
                <div className="analytics-summary-team">
                  <img
                    src={getLogoUrl(summary.awayTeam.teamId)}
                    alt={summary.awayTeam.teamName}
                    className="analytics-summary-logo"
                    onError={(e) => {
                      e.currentTarget.src = placeholderTeamLogoUrl;
                    }}
                  />
                  <div className="analytics-summary-team-info">
                    <div className="analytics-summary-name">{summary.awayTeam.teamName}</div>
                    <div className={`analytics-summary-score ${awayWinning ? "winner" : ""}`}>
                      {summary.awayTeam.score}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Player Tables */}
        <A5PlayerTable team={game.homeTeam} />
        <A5PlayerTable team={game.awayTeam} />
      </div>
    </div>
  );
};

interface PlayerTableProps {
  team: Team;
}

const A5PlayerTable = ({team}: PlayerTableProps) => {
  const activePlayers = team.players.filter((player: Player) => player.comment === "");

  return (
    <div className="analytics-player-panel">
      <div className="analytics-player-panel-header">
        <h2 className="analytics-panel-title">{team.teamName}</h2>
        <span className="analytics-panel-badge">{activePlayers.length} players</span>
      </div>
      <div style={{overflowX: "auto"}}>
        <table className="analytics-player-table">
          <thead>
            <tr>
              <th style={{minWidth: "120px"}}>Player</th>
              <th>PTS</th>
              <th>REB</th>
              <th>AST</th>
              <th>STL</th>
              <th>BLK</th>
              <th>TO</th>
              <th>PF</th>
              <th>+/-</th>
              <th>MIN</th>
              <th>FGM</th>
              <th>FGA</th>
              <th>FG%</th>
              <th>3PM</th>
              <th>3PA</th>
              <th>3P%</th>
              <th>FTM</th>
              <th>FTA</th>
              <th>FT%</th>
            </tr>
          </thead>
          <tbody>
            {activePlayers.map((player: Player) => {
              const stats = player.statistics;
              const isHighPoints = stats.points >= 20;
              const isHighRebounds = stats.reboundsTotal >= 10;
              const isHighAssists = stats.assists >= 10;

              return (
                <tr key={player.personId}>
                  <td className="analytics-player-name">{player.nameI}</td>
                  <td className={isHighPoints ? "analytics-stat-highlight" : ""}>
                    {stats.points}
                  </td>
                  <td className={isHighRebounds ? "analytics-stat-highlight" : ""}>
                    {stats.reboundsTotal}
                  </td>
                  <td className={isHighAssists ? "analytics-stat-highlight" : ""}>
                    {stats.assists}
                  </td>
                  <td>{stats.steals}</td>
                  <td>{stats.blocks}</td>
                  <td>{stats.turnovers}</td>
                  <td>{stats.foulsPersonal}</td>
                  <td>{stats.plusMinusPoints > 0 ? `+${stats.plusMinusPoints}` : stats.plusMinusPoints}</td>
                  <td>{formatMinutesPlayed(stats.minutes)}</td>
                  <td>{stats.fieldGoalsMade}</td>
                  <td>{stats.fieldGoalsAttempted}</td>
                  <td>{(stats.fieldGoalsPercentage * 100).toFixed(0)}%</td>
                  <td>{stats.threePointersMade}</td>
                  <td>{stats.threePointersAttempted}</td>
                  <td>{(stats.threePointersPercentage * 100).toFixed(0)}%</td>
                  <td>{stats.freeThrowsMade}</td>
                  <td>{stats.freeThrowsAttempted}</td>
                  <td>{(stats.freeThrowsPercentage * 100).toFixed(0)}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default A5Boxscore;

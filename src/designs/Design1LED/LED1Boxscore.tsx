import {useQuery} from "@tanstack/react-query";
import {useParams, Link} from "react-router-dom";
import {useTheme} from "@/hooks/useTheme";
import DarkModeToggle from "@/components/DarkModeToggle";
import {getBoxScores, getGameSummary} from "@/services/nbaService";
import {formatMinutesPlayed, placeholderTeamLogoUrl} from "@/helpers/helpers";
import type {Player, Team} from "@/helpers/helpers";
import "./design1.css";

const LED1Boxscore = () => {
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
      <div className={`led-container ${theme}`}>
        <div className="led-loading">Loading Boxscore...</div>
      </div>
    );
  }

  if (boxscoreQuery.isError || !boxscoreQuery.data) {
    return (
      <div className={`led-container ${theme}`}>
        <div className="led-no-games">Error loading boxscore</div>
      </div>
    );
  }

  const {game} = boxscoreQuery.data;
  const summary = gameSummaryQuery.data;

  const getLogoUrl = (teamId: number) => `https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`;

  return (
    <div className={`led-container ${theme}`}>
      <div style={{position: "absolute", top: "1rem", right: "1rem", zIndex: 10}}>
        <DarkModeToggle />
      </div>

      <Link to="/1" className="led-back-link">
        ← Back to Scores
      </Link>

      <div className="led-boxscore-container">
        {/* Game Summary */}
        {summary && (
          <div className="led-game-summary">
            {/* Home Team */}
            <div className="led-summary-team">
              <img
                src={getLogoUrl(summary.homeTeam.teamId)}
                alt={summary.homeTeam.teamName}
                className="led-summary-logo"
                onError={(e) => {
                  e.currentTarget.src = placeholderTeamLogoUrl;
                }}
              />
              <div className="led-summary-name">{summary.homeTeam.teamName}</div>
              <div className={`led-summary-score ${Number(summary.homeTeam.score) > Number(summary.awayTeam.score) ? "winner" : ""}`}>
                {summary.homeTeam.score}
              </div>
            </div>

            {/* Quarter Table */}
            <table className="led-quarter-table">
              <thead>
                <tr>
                  <th></th>
                  <th>1</th>
                  <th>2</th>
                  <th>3</th>
                  <th>4</th>
                  {summary.homeTeam.periods.slice(4).map((p: {period: number}) => (
                    <th key={`ot-${p.period}`}>OT{p.period - 4}</th>
                  ))}
                  <th>T</th>
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

            {/* Away Team */}
            <div className="led-summary-team">
              <img
                src={getLogoUrl(summary.awayTeam.teamId)}
                alt={summary.awayTeam.teamName}
                className="led-summary-logo"
                onError={(e) => {
                  e.currentTarget.src = placeholderTeamLogoUrl;
                }}
              />
              <div className="led-summary-name">{summary.awayTeam.teamName}</div>
              <div className={`led-summary-score ${Number(summary.awayTeam.score) > Number(summary.homeTeam.score) ? "winner" : ""}`}>
                {summary.awayTeam.score}
              </div>
            </div>
          </div>
        )}

        {/* Player Tables */}
        <LED1PlayerTable team={game.homeTeam} />
        <LED1PlayerTable team={game.awayTeam} />
      </div>
    </div>
  );
};

interface PlayerTableProps {
  team: Team;
}

const LED1PlayerTable = ({team}: PlayerTableProps) => {
  const activePlayers = team.players.filter((player: Player) => player.comment === "");

  return (
    <div className="led-player-table-wrapper">
      <h2 className="led-table-header">{team.teamName}</h2>
      <div style={{overflowX: "auto"}}>
        <table className="led-player-table">
          <thead>
            <tr>
              <th style={{minWidth: "120px"}}>PLAYER</th>
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
                  <td className="led-player-name">
                    {player.nameI}
                  </td>
                  <td className={isHighPoints ? "led-stat-highlight" : ""}>
                    {stats.points}
                  </td>
                  <td className={isHighRebounds ? "led-stat-highlight" : ""}>
                    {stats.reboundsTotal}
                  </td>
                  <td className={isHighAssists ? "led-stat-highlight" : ""}>
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

export default LED1Boxscore;

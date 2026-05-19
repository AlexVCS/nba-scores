interface PlayoffBracketProps {
  conferenceName: string;
  playoffPicture: Record<string, unknown>[];
}

function PlayoffBracket({ conferenceName, playoffPicture }: PlayoffBracketProps) {
  if (!playoffPicture || playoffPicture.length === 0) {
    return <p>No playoff data available</p>;
  }

  // Log the structure so we can see the actual field names
  if (playoffPicture.length > 0) {
    console.log(`${conferenceName} playoff_picture structure:`, playoffPicture[0]);
  }

  return (
    <div className="mb-8">
      <h2 className="text-2xl font-bold mb-4 dark:text-slate-50">{conferenceName} Bracket</h2>
      <div className="space-y-4">
        {playoffPicture.map((matchup, index) => {
          // Try to extract team names and series data with multiple field name variations
          const getFieldValue = (obj: Record<string, unknown>, fieldNames: string[]) => {
            for (const field of fieldNames) {
              if (field in obj && obj[field] !== null && obj[field] !== undefined) {
                return String(obj[field]);
              }
            }
            return null;
          };

          const team1 = getFieldValue(matchup, [
            "TEAM_NAME_1",
            "team_name_1",
            "TeamName1",
            "Team1",
            "TEAM_1",
          ]);
          const team2 = getFieldValue(matchup, [
            "TEAM_NAME_2",
            "team_name_2",
            "TeamName2",
            "Team2",
            "TEAM_2",
          ]);
          const seed1 = getFieldValue(matchup, [
            "SEED_1",
            "seed_1",
            "Seed1",
            "TEAM_SEED_1",
          ]);
          const seed2 = getFieldValue(matchup, [
            "SEED_2",
            "seed_2",
            "Seed2",
            "TEAM_SEED_2",
          ]);
          const wins1 = getFieldValue(matchup, [
            "SERIES_W_1",
            "series_w_1",
            "SeriesW1",
            "WINS_1",
            "SERIES_WINS_1",
          ]);
          const wins2 = getFieldValue(matchup, [
            "SERIES_W_2",
            "series_w_2",
            "SeriesW2",
            "WINS_2",
            "SERIES_WINS_2",
          ]);

          return (
            <div
              key={index}
              className="border border-gray-300 dark:border-gray-700 rounded p-4 bg-white dark:bg-slate-900"
            >
              <div className="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-3">
                Matchup {index + 1}
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="dark:text-slate-50">
                    {seed1 ? `(${seed1})` : "(?)"} {team1 || "Unknown Team"}
                  </span>
                  <span className="font-bold text-lg dark:text-slate-50">{wins1 || "0"}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="dark:text-slate-50">
                    {seed2 ? `(${seed2})` : "(?)"} {team2 || "Unknown Team"}
                  </span>
                  <span className="font-bold text-lg dark:text-slate-50">{wins2 || "0"}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default PlayoffBracket;

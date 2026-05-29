import { useSearchParams } from "react-router";
import { useEffect, useState } from "react";
import PlayoffYearPicker from "@/components/PlayoffYearPicker";
import { usePlayoffData } from "@/hooks/usePlayoffData";
import PlayoffBracket from "@/components/PlayoffBracket";
import { getDefaultPlayoffSeason } from "@/helpers/helpers";

function Playoffs() {
  const [searchParams] = useSearchParams();
  const seasonParam = searchParams.get("season");
  const [season, setSeason] = useState<string | null>(seasonParam);

  // Auto-load default season if no season param is present
  useEffect(() => {
    if (!seasonParam) {
      setSeason(getDefaultPlayoffSeason());
    } else {
      setSeason(seasonParam);
    }
  }, [seasonParam]);

  const { data, isLoading, error } = usePlayoffData(season);

  useEffect(() => {
    if (data) {
      console.log("Playoff Picture Data:", data);
    }
  }, [data]);

  return (
    <div className="p-4">
      <h1 className="text-3xl font-bold mb-6 dark:text-slate-50">Playoffs</h1>
      <PlayoffYearPicker />
      {isLoading && <p>Loading...</p>}
      {error && <p>Error: {String(error)}</p>}
      {data && (
        <div className="mt-8">
          <PlayoffBracket
            conferenceName="Eastern Conference"
            playoffPicture={data.series}
          />
          <PlayoffBracket
            conferenceName="Western Conference"
            playoffPicture={data.series}
          />
        </div>
      )}
    </div>
  );
}

export default Playoffs;

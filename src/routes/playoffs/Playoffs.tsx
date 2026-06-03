import { useSearchParams } from "react-router";
import { useEffect, useState } from "react";
import PlayoffYearPicker from "@/components/PlayoffYearPicker";
import { usePlayoffData } from "@/hooks/usePlayoffData";
import PlayoffBracketFlow from "@/components/PlayoffBracketFlow";
import { getDefaultPlayoffSeason } from "@/helpers/helpers";

function Playoffs() {
  const [searchParams] = useSearchParams();
  const seasonParam = searchParams.get("season");
  const [season, setSeason] = useState<string | null>(seasonParam);

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
          <PlayoffBracketFlow
            playoffPicture={data.series}
            season={data.season}
          />
        </div>
      )}
    </div>
  );
}

export default Playoffs;

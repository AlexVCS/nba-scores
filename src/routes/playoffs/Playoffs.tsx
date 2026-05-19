import { useSearchParams } from "react-router";
import { useEffect } from "react";
import PlayoffYearPicker from "@/components/PlayoffYearPicker";
import { usePlayoffData } from "@/hooks/usePlayoffData";
import PlayoffBracket from "@/components/PlayoffBracket";

function Playoffs() {
   const [searchParams] = useSearchParams();
  const seasonId = searchParams.get("seasonId");
  const { data, isLoading, error } = usePlayoffData(seasonId);

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
            playoffPicture={data.east.playoff_picture}
          />
          <PlayoffBracket
            conferenceName="Western Conference"
            playoffPicture={data.west.playoff_picture}
          />
        </div>
      )}
    </div>
  );
}

export default Playoffs;

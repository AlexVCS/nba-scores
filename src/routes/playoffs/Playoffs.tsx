import { useSearchParams, Link } from "react-router";
import { useEffect, useState } from "react";
import PlayoffYearPicker from "@/components/PlayoffYearPicker";
import { usePlayoffData } from "@/hooks/usePlayoffData";
import PlayoffBracketFlow from "@/components/PlayoffBracketFlow";
import DarkModeToggle from "@/components/DarkModeToggle";
import Header from "@/components/Header";
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

  return (
    <div className="bg-slate-50 dark:bg-neutral-950">
      <div className="flex justify-between items-center px-4 py-2">
        <DarkModeToggle />
        <Link
          to="/"
          className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-semibold"
        >
          Scorez!
        </Link>
      </div>
      <Header variant="playoffs" />
      <div className="p-4">
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
    </div>
  );
}

export default Playoffs;

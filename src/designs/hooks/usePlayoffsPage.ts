import {useSearchParams} from "react-router";
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import {usePlayoffData} from "@/hooks/usePlayoffData";

export function usePlayoffsPage() {
  const [searchParams] = useSearchParams();
  const season = searchParams.get("season") || getDefaultPlayoffSeason();

  return usePlayoffData(season);
}

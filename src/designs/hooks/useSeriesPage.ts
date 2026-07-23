import {useMemo} from "react";
import {useParams, useSearchParams} from "react-router";
import {usePlayoffData} from "@/hooks/usePlayoffData";
import {buildPlayoffBracketModel} from "@/utils/playoffBracketModel";
import {findSeriesBySlug, yearToSeason} from "@/utils/seriesSlug";

export function useSeriesPage() {
  const {year, seriesSlug} = useParams<{year: string; seriesSlug: string}>();
  const isValidYear = !!year && /^\d{4}$/.test(year);
  const season = isValidYear ? yearToSeason(year) : null;
  const [searchParams, setSearchParams] = useSearchParams();
  const isRevealed = searchParams.get("revealed") === "true";
  const query = usePlayoffData(season);
  const model = useMemo(() => query.data ? buildPlayoffBracketModel(query.data) : null, [query.data]);
  const series = useMemo(
    () => model ? findSeriesBySlug(seriesSlug ?? "", model.series) : undefined,
    [model, seriesSlug],
  );

  const setIsRevealed = (value: boolean) => setSearchParams((previous) => {
    const next = new URLSearchParams(previous);
    if (value) next.set("revealed", "true");
    else next.delete("revealed");
    return next;
  }, {replace: true});

  return {
    ...query,
    year,
    season,
    model,
    series,
    isValidYear,
    isRevealed,
    setIsRevealed,
  };
}

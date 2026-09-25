import {useEffect, useState} from "react";
import {useQuery} from "@tanstack/react-query";
import {format} from "date-fns";
import {useSearchParams} from "react-router";
import {getItem, setItem} from "@/helpers/helpers";
import type {GameData} from "@/helpers/helpers";
import {getScores} from "@/services/nbaService";

interface ScoresResponse {
  games: GameData[];
  nextGameDate?: string | null;
}

interface ScoresPageOptions {
  persistScoreReveal?: boolean;
}

export function useScoresPage({persistScoreReveal = true}: ScoresPageOptions = {}) {
  const [searchParams, setSearchParams] = useSearchParams({date: ""});
  const dateParam = searchParams.get("date") ?? "";
  const today = format(new Date(), "yyyy-MM-dd");
  const [showScores, setShowScores] = useState<boolean>(() => {
    if (!persistScoreReveal) return false;
    const stored = getItem("showScores");
    return typeof stored === "boolean" ? stored : false;
  });

  useEffect(() => {
    if (persistScoreReveal) setItem("showScores", showScores);
  }, [persistScoreReveal, showScores]);

  const query = useQuery({
    queryKey: ["games", dateParam || `default-${today}`],
    queryFn: () => getScores(dateParam) as Promise<ScoresResponse>,
  });

  const nextDate = !dateParam ? query.data?.nextGameDate : null;
  useEffect(() => {
    if (!nextDate) return;
    setSearchParams((params) => {
      const updated = new URLSearchParams(params);
      updated.set("date", nextDate);
      return updated;
    }, {replace: true});
  }, [nextDate, setSearchParams]);

  const games = query.data?.games ?? [];

  return {
    dateParam,
    games,
    showScores,
    setShowScores,
    hasStartedGames: games.some((game) => game.gameStatus !== 1),
    isLoading: query.isLoading || !!nextDate,
    isFetching: query.isFetching,
    error: query.error,
    refetch: query.refetch,
    hasData: query.data !== undefined,
  };
}

import {useEffect, useState} from "react";
import {useQuery} from "@tanstack/react-query";
import {useSearchParams} from "react-router";
import {getItem, setItem} from "@/helpers/helpers";
import type {GameData} from "@/helpers/helpers";
import {getScores} from "@/services/nbaService";

interface ScoresResponse {
  games: GameData[];
}

export function useScoresPage() {
  const [searchParams] = useSearchParams({date: ""});
  const dateParam = searchParams.get("date") ?? "";
  const [showScores, setShowScores] = useState<boolean>(() => {
    const stored = getItem("showScores");
    return typeof stored === "boolean" ? stored : false;
  });

  useEffect(() => setItem("showScores", showScores), [showScores]);

  const query = useQuery({
    queryKey: ["games", dateParam],
    queryFn: () => getScores(dateParam) as Promise<ScoresResponse>,
  });

  const games = query.data?.games ?? [];

  return {
    dateParam,
    games,
    showScores,
    setShowScores,
    hasStartedGames: games.some((game) => game.gameStatus !== 1),
    isLoading: query.isLoading,
    error: query.error,
    hasData: query.data !== undefined,
  };
}

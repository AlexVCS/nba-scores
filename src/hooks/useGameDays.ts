import {useQuery} from "@tanstack/react-query";
import {getGameDays} from "@/services/nbaService";

export function useGameDays(year: number, month: number) {
  const query = useQuery({
    queryKey: ["gameDays", year, month],
    queryFn: () => getGameDays(year, month),
    staleTime: 1000 * 60 * 60,
    gcTime: 1000 * 60 * 60 * 24,
    enabled: year > 0 && month > 0,
  });

  const gameDays = new Set(query.data?.game_days ?? []);

  return {
    gameDays,
    isLoading: query.isLoading,
    error: query.error,
    season: query.data?.season,
  };
}

import { useQuery } from "@tanstack/react-query";
import { getPlayoffPicture } from "@/services/nbaService";
import type { PlayoffBracketResponse } from "@/helpers/helpers";

export const usePlayoffData = (seasonId: string | null) => {
  const query = useQuery({
    queryKey: ["playoffData", seasonId],
    queryFn: () => {
      if (!seasonId) return Promise.reject(new Error("No season ID"));
      return getPlayoffPicture(seasonId);
    },
    enabled: !!seasonId,
    staleTime: 1000 * 60 * 60,
    gcTime: 1000 * 60 * 60 * 24,
  });

  return {
    data: query.data as PlayoffBracketResponse | undefined,
    isLoading: query.isLoading,
    error: query.error,
  };
};

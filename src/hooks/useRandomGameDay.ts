import {useMemo, useState} from "react";
import {useQuery} from "@tanstack/react-query";
import {getRecentGameDays} from "@/services/nbaService";

const GAME_DAYS_MIN_YEAR = 2000;
const GAME_DAYS_MAX_YEAR = 2100;

export const formatGameDateParam = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export const parseGameDateParam = (dateParam: string): Date | undefined => {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateParam);
  if (!match) return undefined;

  const [, year, month, day] = match;
  const date = new Date(Number(year), Number(month) - 1, Number(day));
  return formatGameDateParam(date) === dateParam ? date : undefined;
};

const isSupportedYear = (date: Date): boolean => {
  const year = date.getFullYear();
  return year >= GAME_DAYS_MIN_YEAR && year <= GAME_DAYS_MAX_YEAR;
};

export const chooseRandomGameDay = (
  dates: string[],
  fallbackDate: string,
  randomIndex?: number,
): string => {
  if (dates.length === 0) return fallbackDate;
  const index = randomIndex ?? Math.floor(Math.random() * dates.length);
  return dates[Math.abs(index) % dates.length];
};

interface UseRandomGameDayOptions {
  dateParam?: string;
  today?: Date;
  randomIndex?: number;
}

export function useRandomGameDay({
  dateParam,
  today,
  randomIndex,
}: UseRandomGameDayOptions = {}) {
  const [fallbackToday] = useState(() => new Date());
  const selectedDate = useMemo(() => parseGameDateParam(dateParam ?? ""), [dateParam]);
  const activeDate = useMemo(
    () => selectedDate ?? today ?? fallbackToday,
    [fallbackToday, selectedDate, today],
  );
  const supported = isSupportedYear(activeDate);
  const activeDateParam = formatGameDateParam(activeDate);
  const query = useQuery({
    queryKey: ["recentGameDays", activeDateParam],
    queryFn: () => getRecentGameDays(activeDateParam),
    enabled: supported,
    staleTime: 1000 * 60 * 60,
    gcTime: 1000 * 60 * 60 * 24,
    retry: 1,
  });

  const previousDate = useMemo(() => {
    const date = new Date(activeDate);
    date.setDate(date.getDate() - 1);
    return formatGameDateParam(date);
  }, [activeDate]);
  const isLoading = supported && query.isPending;
  const gameDays = query.data?.game_days;
  const availableDates = useMemo(() => {
    if (isLoading) return [];
    return [...new Set(gameDays ?? [])]
      .filter((candidate) => candidate < activeDateParam)
      .sort((a, b) => b.localeCompare(a));
  }, [activeDateParam, gameDays, isLoading]);
  const availableDatesKey = availableDates.join(",");
  const randomGameDay = useMemo(() => {
    if (isLoading) return undefined;
    const stableAvailableDates = availableDatesKey ? availableDatesKey.split(",") : [];
    return chooseRandomGameDay(stableAvailableDates, previousDate, randomIndex);
  }, [availableDatesKey, isLoading, previousDate, randomIndex]);
  const lastGameDay = availableDates[0] ?? previousDate;

  return {
    activeDate,
    isLoading,
    lastGameDay,
    previousDate,
    randomGameDay,
    selectedDate,
  };
}

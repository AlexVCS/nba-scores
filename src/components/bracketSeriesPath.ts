import {createContext, useContext} from "react";
import {seasonToYear} from "@/utils/seriesSlug";

export type SeriesPathBuilder = (season: string, seriesSlug: string) => string;

export const defaultSeriesPath: SeriesPathBuilder = (season, seriesSlug) =>
  `/playoffs/${seasonToYear(season)}/${seriesSlug}`;

export const BracketSeriesPathContext = createContext<SeriesPathBuilder>(defaultSeriesPath);

export const useBracketSeriesPath = () => useContext(BracketSeriesPathContext);

import {useQuery} from "@tanstack/react-query";
import {useState, useEffect} from "react";
import {useSearchParams} from "react-router";
import {setItem, getItem} from "@/helpers/helpers";
import type {GameData} from "./types";

export const useGamesData = () => {
  const [searchParams] = useSearchParams({date: ""});
  const dateParam: string = searchParams.get("date") ?? "";
  const [showScores, setShowScores] = useState(() => {
    const item = getItem("showScores");
    return item === undefined ? false : item;
  });

  useEffect(() => {
    setItem("showScores", showScores);
  }, [showScores]);

  const getScores = async (dateParam: string): Promise<{games: GameData[]}> => {
    try {
      const baseUrl = import.meta.env.DEV
        ? import.meta.env.VITE_API_URL_DEV
        : import.meta.env.VITE_API_URL_PROD;
      
      const url = dateParam 
        ? `${baseUrl}/?date=${dateParam}` 
        : `${baseUrl}/`;

      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return response.json();
    } catch (error) {
      console.error(`This call didn't work, this is the ${error}`);
      throw error;
    }
  };

  const {isLoading, data, error} = useQuery({
    queryKey: ["games", dateParam],
    queryFn: () => getScores(dateParam),
  });

  return {
    isLoading,
    data,
    error,
    showScores,
    setShowScores,
    dateParam,
  };
};

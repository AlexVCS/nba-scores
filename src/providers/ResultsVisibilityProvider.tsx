import {useCallback, useEffect, useMemo, useState, type ReactNode} from "react";
import {ResultsVisibilityContext} from "@/context/ResultsVisibilityContext";

export const RESULTS_VISIBILITY_STORAGE_KEY = "nba-scorez:design-1:show-all-results";
const LEGACY_RESULTS_VISIBILITY_STORAGE_KEY = "nba-scorez:design-4:show-all-results";

interface ResultsVisibilityProviderProps {
  children: ReactNode;
}

function readStoredPreference(): boolean {
  if (typeof window === "undefined") return false;

  try {
    const storedPreference = window.localStorage.getItem(RESULTS_VISIBILITY_STORAGE_KEY)
      ?? window.localStorage.getItem(LEGACY_RESULTS_VISIBILITY_STORAGE_KEY);
    return storedPreference === "true";
  } catch (error) {
    console.log(error);
    return false;
  }
}

export function ResultsVisibilityProvider({children}: ResultsVisibilityProviderProps) {
  const [showAllResults, setShowAllResults] = useState(readStoredPreference);

  useEffect(() => {
    try {
      window.localStorage.setItem(RESULTS_VISIBILITY_STORAGE_KEY, JSON.stringify(showAllResults));
    } catch (error) {
      console.log(error);
    }
  }, [showAllResults]);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key !== RESULTS_VISIBILITY_STORAGE_KEY) return;
      setShowAllResults(event.newValue === "true");
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const toggleShowAllResults = useCallback(() => {
    setShowAllResults(previous => !previous);
  }, []);

  const value = useMemo(() => ({
    showAllResults,
    setShowAllResults,
    toggleShowAllResults,
  }), [showAllResults, toggleShowAllResults]);

  return (
    <ResultsVisibilityContext.Provider value={value}>
      {children}
    </ResultsVisibilityContext.Provider>
  );
}

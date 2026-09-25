import {useCallback, useEffect, useMemo, useState, type ReactNode} from "react";
import {ResultsVisibilityContext} from "@/context/ResultsVisibilityContext";

export const RESULTS_VISIBILITY_STORAGE_KEY = "nba-scorez:design-1:show-all-results";
export const SPOILER_ONBOARDING_STORAGE_KEY = "nba-scorez:design-1:spoiler-onboarding:v1:dismissed";
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

function readStoredDismissal(): boolean {
  if (typeof window === "undefined") return false;

  try {
    return window.localStorage.getItem(SPOILER_ONBOARDING_STORAGE_KEY) === "true";
  } catch (error) {
    console.log(error);
    return false;
  }
}

export function ResultsVisibilityProvider({children}: ResultsVisibilityProviderProps) {
  const [{showAllResults, isSpoilerHintDismissed}, setVisibility] = useState(() => {
    const showAllResults = readStoredPreference();
    return {
      showAllResults,
      isSpoilerHintDismissed: showAllResults || readStoredDismissal(),
    };
  });

  const setShowAllResults = useCallback((value: boolean) => {
    setVisibility(previous => ({
      showAllResults: value,
      isSpoilerHintDismissed: previous.isSpoilerHintDismissed || value,
    }));
  }, []);

  const dismissSpoilerHint = useCallback(() => {
    setVisibility(previous => previous.isSpoilerHintDismissed
      ? previous
      : {...previous, isSpoilerHintDismissed: true});
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(RESULTS_VISIBILITY_STORAGE_KEY, JSON.stringify(showAllResults));
    } catch (error) {
      console.log(error);
    }
  }, [showAllResults]);

  useEffect(() => {
    if (!isSpoilerHintDismissed) return;

    try {
      window.localStorage.setItem(SPOILER_ONBOARDING_STORAGE_KEY, "true");
    } catch (error) {
      console.log(error);
    }
  }, [isSpoilerHintDismissed]);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      try {
        if (event.storageArea && event.storageArea !== window.localStorage) return;
      } catch (error) {
        console.log(error);
        return;
      }

      if (event.key === RESULTS_VISIBILITY_STORAGE_KEY) {
        setShowAllResults(event.newValue === "true");
      } else if (event.key === SPOILER_ONBOARDING_STORAGE_KEY && event.newValue === "true") {
        dismissSpoilerHint();
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [dismissSpoilerHint, setShowAllResults]);

  const toggleShowAllResults = useCallback(() => {
    setVisibility(previous => ({
      showAllResults: !previous.showAllResults,
      isSpoilerHintDismissed: previous.isSpoilerHintDismissed || !previous.showAllResults,
    }));
  }, []);

  const value = useMemo(() => ({
    showAllResults,
    setShowAllResults,
    toggleShowAllResults,
    isSpoilerHintDismissed,
    dismissSpoilerHint,
  }), [showAllResults, setShowAllResults, toggleShowAllResults, isSpoilerHintDismissed, dismissSpoilerHint]);

  return (
    <ResultsVisibilityContext.Provider value={value}>
      {children}
    </ResultsVisibilityContext.Provider>
  );
}

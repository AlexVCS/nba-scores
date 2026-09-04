import {useContext} from "react";
import {ResultsVisibilityContext} from "@/context/ResultsVisibilityContext";

export function useResultsVisibility() {
  const context = useContext(ResultsVisibilityContext);
  if (context === undefined) {
    throw new Error("useResultsVisibility must be used within a ResultsVisibilityProvider");
  }
  return context;
}

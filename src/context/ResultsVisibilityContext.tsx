import {createContext} from "react";

export interface ResultsVisibilityContextValue {
  showAllResults: boolean;
  setShowAllResults: (value: boolean) => void;
  toggleShowAllResults: () => void;
  isSpoilerHintDismissed: boolean;
  dismissSpoilerHint: () => void;
}

export const ResultsVisibilityContext = createContext<ResultsVisibilityContextValue | undefined>(undefined);

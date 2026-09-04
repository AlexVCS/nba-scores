import type {ComponentType} from "react";
import Design1Boxscore from "./design-1/BoxscorePage";
import Design1Playoffs from "./design-1/PlayoffsPage";
import Design1Scores from "./design-1/ScoresPage";
import Design1Series from "./design-1/SeriesPage";
import type {AlternateDesignId, DesignPage} from "./types";

type DesignPages = Record<DesignPage, ComponentType>;

export const DESIGN_PAGE_COMPONENTS: Record<AlternateDesignId, DesignPages> = {
  "design-1": {
    scores: Design1Scores,
    boxscore: Design1Boxscore,
    playoffs: Design1Playoffs,
    series: Design1Series,
  },
};

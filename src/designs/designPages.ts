import type {ComponentType} from "react";
import Design1Scores from "./design-1/ScoresPage";
import Design1Boxscore from "./design-1/BoxscorePage";
import Design1Playoffs from "./design-1/PlayoffsPage";
import Design1Series from "./design-1/SeriesPage";
import Design2Scores from "./design-2/ScoresPage";
import Design2Boxscore from "./design-2/BoxscorePage";
import Design2Playoffs from "./design-2/PlayoffsPage";
import Design2Series from "./design-2/SeriesPage";
import Design3Scores from "./design-3/ScoresPage";
import Design3Boxscore from "./design-3/BoxscorePage";
import Design3Playoffs from "./design-3/PlayoffsPage";
import Design3Series from "./design-3/SeriesPage";
import Design4Scores from "./design-4/ScoresPage";
import Design4Boxscore from "./design-4/BoxscorePage";
import Design4Playoffs from "./design-4/PlayoffsPage";
import Design4Series from "./design-4/SeriesPage";
import Design5Scores from "./design-5/ScoresPage";
import Design5Boxscore from "./design-5/BoxscorePage";
import Design5Playoffs from "./design-5/PlayoffsPage";
import Design5Series from "./design-5/SeriesPage";
import type {AlternateDesignId, DesignPage} from "./types";

export const DESIGN_PAGE_COMPONENTS: Record<AlternateDesignId, Record<DesignPage, ComponentType>> = {
  "design-1": {scores: Design1Scores, boxscore: Design1Boxscore, playoffs: Design1Playoffs, series: Design1Series},
  "design-2": {scores: Design2Scores, boxscore: Design2Boxscore, playoffs: Design2Playoffs, series: Design2Series},
  "design-3": {scores: Design3Scores, boxscore: Design3Boxscore, playoffs: Design3Playoffs, series: Design3Series},
  "design-4": {scores: Design4Scores, boxscore: Design4Boxscore, playoffs: Design4Playoffs, series: Design4Series},
  "design-5": {scores: Design5Scores, boxscore: Design5Boxscore, playoffs: Design5Playoffs, series: Design5Series},
};

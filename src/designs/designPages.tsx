import type {ComponentType} from "react";
import Design2Boxscore from "./design-2/BoxscorePage";
import Design4Boxscore from "./design-4/BoxscorePage";
import Design4Playoffs from "./design-4/PlayoffsPage";
import Design4Scores from "./design-4/ScoresPage";
import Design4Series from "./design-4/SeriesPage";
import DesignBoxscorePage from "./shared/DesignBoxscorePage";
import DesignPlayoffsPage from "./shared/DesignPlayoffsPage";
import DesignScoresPage from "./shared/DesignScoresPage";
import DesignSeriesPage from "./shared/DesignSeriesPage";
import type {AlternateDesignId, DesignPage} from "./types";

type DesignPages = Record<DesignPage, ComponentType>;

function sharedPages(designId: AlternateDesignId): DesignPages {
  return {
    scores: () => <DesignScoresPage designId={designId} />,
    boxscore: () => <DesignBoxscorePage designId={designId} />,
    playoffs: () => <DesignPlayoffsPage designId={designId} />,
    series: () => <DesignSeriesPage designId={designId} />,
  };
}

export const DESIGN_PAGE_COMPONENTS: Record<AlternateDesignId, DesignPages> = {
  "design-1": sharedPages("design-1"),
  "design-2": {...sharedPages("design-2"), boxscore: Design2Boxscore},
  "design-3": sharedPages("design-3"),
  "design-4": {
    scores: Design4Scores,
    boxscore: Design4Boxscore,
    playoffs: Design4Playoffs,
    series: Design4Series,
  },
};

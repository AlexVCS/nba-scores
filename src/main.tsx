import {StrictMode} from "react";
import {createRoot} from "react-dom/client";
import "./index.css";
import App from "./App";
import Boxscore from "./routes/games/boxscore/Boxscore";
import Playoffs from "./routes/playoffs/Playoffs";
import SeriesDetail from "./routes/playoffs/SeriesDetail";
import BoxscoreDesign from "./routes/designs/boxscore/BoxscoreDesign";
import BoxscoreBentoDesign from "./routes/designs/boxscore/BoxscoreBentoDesign";
import PlayoffzDesign from "./routes/designs/playoffz/PlayoffzDesign";
import PlayoffzMapDesign from "./routes/designs/playoffz/PlayoffzMapDesign";
import SeriesDetailDesign from "./routes/designs/playoffz/SeriesDetailDesign";
import SeriesFeatureDesign from "./routes/designs/playoffz/SeriesFeatureDesign";
import ScorezArcadeDesign from "./routes/designs/scorez/ScorezArcadeDesign";
import ScorezCoverflowDesign from "./routes/designs/scorez/ScorezCoverflowDesign";
import ScorezDesign from "./routes/designs/scorez/ScorezDesign";
import ScorezMasonryDesign from "./routes/designs/scorez/ScorezMasonryDesign";
import {BrowserRouter, Routes, Route} from "react-router";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {Provider, defaultTheme} from "@adobe/react-spectrum";
import {ThemeProvider} from "./providers/ThemeProvider.jsx";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Provider theme={defaultTheme}>
        <ThemeProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<App />} />
              <Route path="/playoffs" element={<Playoffs />} />
              <Route path="/playoffs/:year/:seriesSlug" element={<SeriesDetail />} />
              <Route path="games/:gameId/boxscore" element={<Boxscore />} />
              <Route path="/designs/scorez" element={<ScorezDesign />} />
              <Route path="/designs/scorez-arcade" element={<ScorezArcadeDesign />} />
              <Route path="/designs/scorez-masonry" element={<ScorezMasonryDesign />} />
              <Route path="/designs/scorez-coverflow" element={<ScorezCoverflowDesign />} />
              <Route path="/designs/playoffz" element={<PlayoffzDesign />} />
              <Route path="/designs/playoffz-map" element={<PlayoffzMapDesign />} />
              <Route path="/designs/playoffz/:year/:seriesSlug" element={<SeriesDetailDesign />} />
              <Route path="/designs/series-feature/:year/:seriesSlug" element={<SeriesFeatureDesign />} />
              <Route path="/designs/boxscore/:gameId" element={<BoxscoreDesign />} />
              <Route path="/designs/boxscore-bento/:gameId" element={<BoxscoreBentoDesign />} />
            </Routes>
          </BrowserRouter>
        </ThemeProvider>
      </Provider>
    </QueryClientProvider>
  </StrictMode>
);

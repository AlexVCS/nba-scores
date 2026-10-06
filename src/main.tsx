import {StrictMode} from "react";
import {createRoot} from "react-dom/client";
import "./index.css";
import {BrowserRouter, Navigate, Routes, Route} from "react-router";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {ThemeProvider} from "./providers/ThemeProvider.jsx";
import {ResultsVisibilityProvider} from "./providers/ResultsVisibilityProvider";
import DesignRoute from "./designs/DesignRoute";
import LegacyDesignRedirect from "./designs/LegacyDesignRedirect";
import ScoresPage from "./designs/design-1/ScoresPage";
import BoxscorePage from "./designs/design-1/BoxscorePage";
import PlayoffsPage from "./designs/design-1/PlayoffsPage";
import SeriesPage from "./designs/design-1/SeriesPage";
import "./designs/designs.css";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ResultsVisibilityProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<DesignRoute><ScoresPage /></DesignRoute>} />
              <Route path="/playoffs" element={<DesignRoute><PlayoffsPage /></DesignRoute>} />
              <Route path="/playoffs/:year/:seriesSlug" element={<DesignRoute><SeriesPage /></DesignRoute>} />
              <Route path="/games/:gameId/boxscore" element={<DesignRoute><BoxscorePage /></DesignRoute>} />
              <Route path="/design-1/*" element={<LegacyDesignRedirect />} />
              <Route path="/original/*" element={<LegacyDesignRedirect />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ResultsVisibilityProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>
);

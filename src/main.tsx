import {Fragment, StrictMode} from "react";
import {createRoot} from "react-dom/client";
import "./index.css";
import App from "./App";
import Boxscore from "./routes/games/boxscore/Boxscore";
import Playoffs from "./routes/playoffs/Playoffs";
import SeriesDetail from "./routes/playoffs/SeriesDetail";
import {BrowserRouter, Navigate, Routes, Route} from "react-router";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {Provider, defaultTheme} from "@adobe/react-spectrum";
import {ThemeProvider} from "./providers/ThemeProvider.jsx";
import {ResultsVisibilityProvider} from "./providers/ResultsVisibilityProvider";
import DesignRoute from "./designs/DesignRoute";
import {ALTERNATE_DESIGNS} from "./designs/designRegistry";
import {DESIGN_PAGE_COMPONENTS} from "./designs/designPages";
import "./designs/designs.css";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Provider theme={defaultTheme}>
        <ThemeProvider>
          <ResultsVisibilityProvider>
            <BrowserRouter>
              <Routes>
              <Route path="/" element={<App />} />
              <Route path="/playoffs" element={<Playoffs />} />
              <Route path="/playoffs/:year/:seriesSlug" element={<SeriesDetail />} />
              <Route path="/games/:gameId/boxscore" element={<Boxscore />} />
              <Route path="/original" element={<DesignRoute designId="original"><App /></DesignRoute>} />
              <Route path="/original/playoffs" element={<DesignRoute designId="original"><Playoffs /></DesignRoute>} />
              <Route path="/original/playoffs/:year/:seriesSlug" element={<DesignRoute designId="original"><SeriesDetail /></DesignRoute>} />
              <Route path="/original/games/:gameId/boxscore" element={<DesignRoute designId="original"><Boxscore /></DesignRoute>} />
              {ALTERNATE_DESIGNS.map((design) => {
                const pages = DESIGN_PAGE_COMPONENTS[design.id];
                return (
                  <Fragment key={design.id}>
                    <Route path={`/${design.id}`} element={<DesignRoute designId={design.id}><pages.scores /></DesignRoute>} />
                    <Route path={`/${design.id}/playoffs`} element={<DesignRoute designId={design.id}><pages.playoffs /></DesignRoute>} />
                    <Route path={`/${design.id}/playoffs/:year/:seriesSlug`} element={<DesignRoute designId={design.id}><pages.series /></DesignRoute>} />
                    <Route path={`/${design.id}/games/:gameId/boxscore`} element={<DesignRoute designId={design.id}><pages.boxscore /></DesignRoute>} />
                  </Fragment>
                );
              })}
              <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </ResultsVisibilityProvider>
        </ThemeProvider>
      </Provider>
    </QueryClientProvider>
  </StrictMode>
);

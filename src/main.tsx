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
import DesignRoute from "./designs/DesignRoute";
import PreviewGate from "./designs/PreviewGate";
import {ALTERNATE_DESIGNS} from "./designs/designRegistry";
import {DESIGN_PAGE_COMPONENTS} from "./designs/designPages";
import {DESIGN_PREVIEW_ROUTE_PATH} from "./designs/previewConfig";
import "./designs/designs.css";

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
              <Route path="/games/:gameId/boxscore" element={<Boxscore />} />
              <Route path={`${DESIGN_PREVIEW_ROUTE_PATH}/original`} element={<PreviewGate><DesignRoute designId="original"><App /></DesignRoute></PreviewGate>} />
              <Route path={`${DESIGN_PREVIEW_ROUTE_PATH}/original/playoffs`} element={<PreviewGate><DesignRoute designId="original"><Playoffs /></DesignRoute></PreviewGate>} />
              <Route path={`${DESIGN_PREVIEW_ROUTE_PATH}/original/playoffs/:year/:seriesSlug`} element={<PreviewGate><DesignRoute designId="original"><SeriesDetail /></DesignRoute></PreviewGate>} />
              <Route path={`${DESIGN_PREVIEW_ROUTE_PATH}/original/games/:gameId/boxscore`} element={<PreviewGate><DesignRoute designId="original"><Boxscore /></DesignRoute></PreviewGate>} />
              {ALTERNATE_DESIGNS.map((design) => {
                const pages = DESIGN_PAGE_COMPONENTS[design.id];
                return (
                  <Fragment key={design.id}>
                    <Route path={`${DESIGN_PREVIEW_ROUTE_PATH}/${design.id}`} element={<PreviewGate><DesignRoute designId={design.id}><pages.scores /></DesignRoute></PreviewGate>} />
                    <Route path={`${DESIGN_PREVIEW_ROUTE_PATH}/${design.id}/playoffs`} element={<PreviewGate><DesignRoute designId={design.id}><pages.playoffs /></DesignRoute></PreviewGate>} />
                    <Route path={`${DESIGN_PREVIEW_ROUTE_PATH}/${design.id}/playoffs/:year/:seriesSlug`} element={<PreviewGate><DesignRoute designId={design.id}><pages.series /></DesignRoute></PreviewGate>} />
                    <Route path={`${DESIGN_PREVIEW_ROUTE_PATH}/${design.id}/games/:gameId/boxscore`} element={<PreviewGate><DesignRoute designId={design.id}><pages.boxscore /></DesignRoute></PreviewGate>} />
                  </Fragment>
                );
              })}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ThemeProvider>
      </Provider>
    </QueryClientProvider>
  </StrictMode>
);

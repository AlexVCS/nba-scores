import {StrictMode} from "react";
import {createRoot} from "react-dom/client";
import "./index.css";
import App from "./App";
import Boxscore from "./routes/games/boxscore/Boxscore";
import {BrowserRouter, Routes, Route} from "react-router";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {Provider, defaultTheme} from "@adobe/react-spectrum";
import {ThemeProvider} from "./providers/ThemeProvider.jsx";

// Design imports
import DesignShowcase from "./designs/Showcase/DesignShowcase";
import LED1Wrapper from "./designs/Design1LED/LED1Wrapper";
import LED1Boxscore from "./designs/Design1LED/LED1Boxscore";
import B2Wrapper from "./designs/Design2Brutalism/B2Wrapper";
import B2Boxscore from "./designs/Design2Brutalism/B2Boxscore";
import C4Wrapper from "./designs/Design4Cyberpunk/C4Wrapper";
import C4Boxscore from "./designs/Design4Cyberpunk/C4Boxscore";
import A5Wrapper from "./designs/Design5Analytics/A5Wrapper";
import A5Boxscore from "./designs/Design5Analytics/A5Boxscore";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Provider theme={defaultTheme}>
        <ThemeProvider>
          <BrowserRouter>
            <Routes>
              {/* Design Showcase - Landing Page */}
              <Route path="/" element={<DesignShowcase />} />
              
              {/* Original App */}
              <Route path="/original" element={<App />} />
              <Route path="games/:gameId/boxscore" element={<Boxscore />} />
              
              {/* Design 1: LED Scoreboard */}
              <Route path="/1" element={<LED1Wrapper />} />
              <Route path="/1/games/:gameId/boxscore" element={<LED1Boxscore />} />
              
              {/* Design 2: Minimalist Brutalism */}
              <Route path="/2" element={<B2Wrapper />} />
              <Route path="/2/games/:gameId/boxscore" element={<B2Boxscore />} />
              
              {/* Design 4: Neon Cyberpunk */}
              <Route path="/4" element={<C4Wrapper />} />
              <Route path="/4/games/:gameId/boxscore" element={<C4Boxscore />} />
              
              {/* Design 5: Sports Analytics Dashboard */}
              <Route path="/5" element={<A5Wrapper />} />
              <Route path="/5/games/:gameId/boxscore" element={<A5Boxscore />} />
            </Routes>
          </BrowserRouter>
        </ThemeProvider>
      </Provider>
    </QueryClientProvider>
  </StrictMode>
);

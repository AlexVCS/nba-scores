// import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Games from "./routes/games/Games.jsx";
import React from "react";
import GameDatePicker from "./components/GameDatePicker.jsx";
// import PageLayout from "./PageLayout.jsx";
import DarkModeToggle from "./components/DarkModeToggle.jsx";
import { ThemeProvider } from "./providers/ThemeProvider.jsx";

function App() {
  return (
    <ThemeProvider>
      <DarkModeToggle />
      <GameDatePicker />
      <Games />
      
      {/* <ReactQueryDevtools /> */}
    </ThemeProvider>
  );
}

export default App;

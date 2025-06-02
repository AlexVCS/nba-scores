// import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Games from "./routes/games/Games.jsx";
import React from "react";
import GameDatePicker from "./components/GameDatePicker.jsx";
// import PageLayout from "./PageLayout.jsx";
import DarkModeToggle from "./components/DarkModeToggle.jsx";
// import Boxscore from "./routes/games/boxscore/Boxscore.jsx";
import Header from "./components/Header.jsx";

function App() {
  return (
    <div className="bg-slate-50 dark:bg-neutral-950">
      <DarkModeToggle />
      <Header />
      <GameDatePicker />
      <Games />
      {/* <ReactQueryDevtools /> */}
    </div>
  );
}

export default App;

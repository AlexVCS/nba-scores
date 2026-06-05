// import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Games from "./routes/games/Games.jsx";
import React from "react";
import { Link } from "react-router";
import GameDatePicker from "./components/GameDatePicker.jsx";
// import PageLayout from "./PageLayout.jsx";
import DarkModeToggle from "./components/DarkModeToggle.jsx";
// import Boxscore from "./routes/games/boxscore/Boxscore.jsx";
import Header from "./components/Header.jsx";

function App() {
  return (
    <div className="bg-slate-50 dark:bg-neutral-950">
      <div className="flex justify-between items-center px-4 py-2">
        <DarkModeToggle />
        <Link
          to="/playoffs"
          className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-semibold"
        >
          Playoffz!
        </Link>
      </div>
      <Header />
      <GameDatePicker />
      <Games />
      {/* <ReactQueryDevtools /> */}
    </div>
  );
}

export default App;

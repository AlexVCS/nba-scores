import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Games from "./routes/games/Games.jsx";
import React from "react";
import GameDatePicker from "./components/GameDatePicker.jsx";
import PageLayout from "./PageLayout.jsx";

function App() {

  return (
    <PageLayout>
      <GameDatePicker />
      <Games />
      <ReactQueryDevtools />
    </PageLayout>
  );
}

export default App;

import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Games from "./routes/games/Games";
import React from "react";
import GameDatePicker from "./components/GameDatePicker";
import PageLayout from "./PageLayout";

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

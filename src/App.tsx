import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Games from "./routes/games/Games";
import React from "react";
import DatePicker from "./components/DatePicker";
import NewDatePicker from "./components/NewDatePicker";
import PageLayout from "./PageLayout";

function App() {

  return (
    <PageLayout>
      <NewDatePicker />
      <DatePicker />
      <Games />
      <ReactQueryDevtools />
    </PageLayout>
  );
}

export default App;

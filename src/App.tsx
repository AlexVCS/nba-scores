import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Header from "./components/Header";
import Games from "./components/Games";
import React from "react";
import DatePicker from "./components/DatePicker";
import {useSearchParams} from "react-router";
import NewDatePicker from "./components/NewDatePicker";

function App() {
  const queryClient = new QueryClient();
  const [searchParams, setSearchParams] = useSearchParams({date: ""});
  type SetURLSearchParams = ReturnType<typeof useSearchParams>[1];

  return (
    <QueryClientProvider client={queryClient}>
      <Header />
      <NewDatePicker />
      <DatePicker setSearchParams={setSearchParams} />
      <Games searchParams={searchParams} />
      <ReactQueryDevtools />
    </QueryClientProvider>
  );
}

export default App;

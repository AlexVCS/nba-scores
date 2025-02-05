import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Header from "./components/Header";
import Scores from "./components/Scores";
import React from 'react'
import DatePicker from "./components/DatePicker";
import {useSearchParams} from "react-router";


function App() {
  const queryClient = new QueryClient();
  const [searchParams, setSearchParams] = useSearchParams({date: ""});


  return (
    <QueryClientProvider client={queryClient}>
      <Header />
      <DatePicker setSearchParams={setSearchParams} />
      <Scores searchParams={searchParams} />
      <ReactQueryDevtools />
    </QueryClientProvider>
  );
}

export default App

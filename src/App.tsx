import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Header from "./components/Header";
import Scores from "./components/Scores";

function App() {
  const queryClient = new QueryClient();

  return (
    <QueryClientProvider client={queryClient} >
      <Header />
      <Scores />
      <ReactQueryDevtools />
    </QueryClientProvider>
  );
}

export default App

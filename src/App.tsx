// import {ReactQueryDevtools} from "@tanstack/react-query-devtools";
import Games from "./routes/games/Games.jsx";
import {useState} from "react";
import GameDatePicker from "./components/GameDatePicker.jsx";
import DarkModeToggle from "./components/DarkModeToggle.jsx";
import Header from "./components/Header.jsx";

function App() {
  const [gamesToday, setGamesToday] = useState<boolean>(false)

  return (
    <div className="bg-slate-50 dark:bg-neutral-950">
      <DarkModeToggle />
      <Header />
      <GameDatePicker  />
      <Games setGamesToday={setGamesToday} />
      {/* <ReactQueryDevtools /> */}
    </div>
  );
}

export default App;

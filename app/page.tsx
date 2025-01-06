import Scores from "@/app/components/Scores";
import DatePicker from "./components/DatePicker";
import ThemeSwitch from './components/ThemeSwitch';
import ShowScores from "./components/ShowScores";

function Home() {

  return (
    <div className="text-center flex flex-col gap-2">
      <h1 className="mt-2">NBA Scores</h1>
      <div className="self-center">
        <ThemeSwitch />
      </div>
     <ShowScores />
      <DatePicker/>
      <Scores />
    </div>
  );
}

export default Home;

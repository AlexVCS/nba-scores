import Scores from "@/app/components/Scores";
import DatePicker from "./components/DatePicker";
import ThemeSwitch from './components/ThemeSwitch';
import ShowScores from "./components/ShowScores";
import { Url } from "url";

function Home({
  searchParams, params
}: {
  searchParams?: {
    selectedDate: string;
  },
  params?: {
    slug: string
  }
}) {
  const selectedDate = searchParams?.selectedDate || '';
  const url = params?.slug

  return (
    <div className="text-center flex flex-col gap-2">
      <h1 className="mt-2">NBA Scores</h1>
      <div className="self-center">
        <ThemeSwitch />
      </div>
     <ShowScores />
      <DatePicker/>
      <Scores selectedDate={selectedDate} url={url} />
    </div>
  );
}

export default Home;

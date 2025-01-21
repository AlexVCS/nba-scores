import Scores from "@/app/components/Scores";
import DatePicker from "./components/DatePicker";
import ThemeSwitch from "./components/ThemeSwitch";
import ShowScores from "./components/ShowScores";

function Home({
  searchParams,
  params,
}: {
  searchParams?: {
    selectedDate: string;
    renderScores: string;
  };
  params?: {
    slug: string;
  };
}) {
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const selectedDate = searchParams?.selectedDate || "";
  const renderScores = searchParams?.renderScores || "";
  
  return (
    <div className="text-center flex flex-col gap-2">
      <h1 className="mt-2">NBA Scores</h1>
      <div className="self-center">
        <ThemeSwitch />
      </div>
      <ShowScores
        userTimezone={userTimezone}
        selectedDate={selectedDate}
        renderScores={renderScores}
      />
      <DatePicker />
      <Scores
        userTimezone={userTimezone}
        renderScores={renderScores}
        selectedDate={selectedDate}
      />
    </div>
  );
}

export default Home;

import {useCallback} from "react";
import {BracketSeriesPathContext} from "@/components/bracketSeriesPath";
import {seasonToYear} from "@/utils/seriesSlug";
import {usePlayoffsPage} from "../hooks/usePlayoffsPage";
import {designPath} from "../designRoutes";
import HardwoodHeader from "./components/HardwoodHeader";
import HardwoodPage from "./components/HardwoodPage";
import HardwoodPageState from "./components/HardwoodPageState";
import HardwoodSeasonPicker from "./components/HardwoodSeasonPicker";
import Design1PlayoffBracket from "./components/Design1PlayoffBracket";
import {hwContainer} from "./components/hardwoodStyles";

function PlayoffsPage() {
  const state = usePlayoffsPage();
  const buildSeriesPath = useCallback(
    (season: string, seriesSlug: string) =>
      designPath("design-1", `/playoffs/${seasonToYear(season)}/${seriesSlug}`),
    [],
  );

  return (
    <HardwoodPage>
      <HardwoodHeader section="playoffs" />
      <section className={`${hwContainer} grid grid-cols-1 items-end justify-items-center gap-[30px] pt-6 pb-7`}>
        <HardwoodSeasonPicker />
      </section>
      {state.isLoading ? <HardwoodPageState kind="loading" /> : state.error ? <HardwoodPageState kind="error" /> : state.data ? (
        <div className="mx-auto mt-1.5 mb-20 w-[min(1680px,calc(100%_-_32px))]">
          <BracketSeriesPathContext.Provider value={buildSeriesPath}>
            <Design1PlayoffBracket playoffPicture={state.data} />
          </BracketSeriesPathContext.Provider>
        </div>
      ) : <HardwoodPageState kind="empty" title="No bracket available" />}
    </HardwoodPage>
  );
}

export default PlayoffsPage;

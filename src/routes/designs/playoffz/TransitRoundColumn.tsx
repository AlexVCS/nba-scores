import {motion} from "framer-motion";
import {cascadeItemVariants} from "@/components/designs/motion/cascadeVariants";
import type {RenderSeries} from "@/utils/playoffBracketModel";
import TransitSeriesStop from "./TransitSeriesStop";

interface TransitRoundColumnProps {
  roundName: string;
  series: RenderSeries[];
  allSeries: RenderSeries[];
  season: string;
  isRevealed: boolean;
}

function TransitRoundColumn({
  roundName,
  series,
  allSeries,
  season,
  isRevealed,
}: TransitRoundColumnProps) {
  return (
    <motion.section
      variants={cascadeItemVariants}
      className="relative min-w-0 md:min-w-[270px]"
    >
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-emerald-300/70 dark:bg-emerald-300/20" />
        <h3 className="text-sm font-black uppercase tracking-[0.2em] text-emerald-800 dark:text-emerald-200">
          {roundName}
        </h3>
      </div>
      <div className="relative grid gap-4 md:border-l-2 md:border-emerald-500/50 md:pl-5">
        {series.map((item) => (
          <TransitSeriesStop
            key={item.seriesKey}
            series={item}
            allSeries={allSeries}
            season={season}
            isRevealed={isRevealed}
          />
        ))}
      </div>
    </motion.section>
  );
}

export default TransitRoundColumn;

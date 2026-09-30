import {useState} from "react";
import type {AskAggregation, AskMeasureValues, AskStatValue} from "@/services/ask/types";

interface MeasuredResult {
  aggregation: AskAggregation;
  values: AskStatValue[];
  alternate: AskMeasureValues | null;
}

/**
 * The measure a season or career line shows. It starts at the server's measure (per game
 * when the question stated none) and can switch to `alternate`, which the server computed
 * from the same source row. Both measures are already in the answer, so switching never
 * refetches and never mixes sources.
 */
export function useAskMeasure(result: MeasuredResult) {
  const [measure, setMeasure] = useState<AskAggregation>(result.aggregation);
  const alternate = result.alternate;
  const showingAlternate = alternate !== null && measure === alternate.aggregation;
  return {
    measure: showingAlternate ? alternate.aggregation : result.aggregation,
    values: showingAlternate ? alternate.values : result.values,
    toggle: alternate !== null,
    setMeasure,
  };
}

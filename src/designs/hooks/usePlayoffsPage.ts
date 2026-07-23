import {useEffect, useMemo, useState} from "react";
import {useSearchParams} from "react-router";
import {getDefaultPlayoffSeason} from "@/helpers/helpers";
import {usePlayoffData} from "@/hooks/usePlayoffData";
import {buildPlayoffBracketModel, canRevealRound as canRevealRoundFromModel} from "@/utils/playoffBracketModel";

export function usePlayoffsPage() {
  const [searchParams] = useSearchParams();
  const seasonParam = searchParams.get("season");
  const [season, setSeason] = useState<string | null>(seasonParam);
  const [revealedRounds, setRevealedRounds] = useState<Set<number>>(new Set());

  useEffect(() => setSeason(seasonParam || getDefaultPlayoffSeason()), [seasonParam]);
  useEffect(() => setRevealedRounds(new Set()), [season]);

  const query = usePlayoffData(season);
  const model = useMemo(() => query.data ? buildPlayoffBracketModel(query.data) : null, [query.data]);

  const revealRound = (round: number) => setRevealedRounds((previous) => new Set([...previous, round]));
  const hideRound = (round: number) => setRevealedRounds((previous) => {
    const next = new Set(previous);
    for (const revealed of next) if (revealed >= round) next.delete(revealed);
    return next;
  });
  const canRevealRound = (round: number) => model
    ? canRevealRoundFromModel(round, model.rounds, revealedRounds)
    : false;

  return {...query, season, model, revealedRounds, revealRound, hideRound, canRevealRound};
}

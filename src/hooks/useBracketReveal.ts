import {useCallback, useEffect, useMemo, useState} from "react";
import type {PlayoffBracketModel} from "@/utils/playoffBracketModel";
import {canRevealRound as canRevealRoundFromModel} from "@/utils/playoffBracketModel";

const HIDDEN_STATUS = "Results are hidden until you choose to reveal them.";

interface RevealState {
  season: string;
  rounds: Set<number>;
}

export interface BracketRevealState {
  revealedRounds: Set<number>;
  statusMessage: string;
  canRevealRound: (round: number) => boolean;
  revealRound: (round: number) => void;
  revealThroughRound: (round: number) => void;
  hideRound: (round: number) => void;
  showAllResults: () => void;
  hideAllResults: () => void;
}

interface BracketRevealOptions {
  forceShowAll?: boolean;
}

/**
 * Owns the spoiler boundary for one bracket. A season change clears every reveal,
 * and hiding a round also hides every round that follows it in model order.
 */
export function useBracketReveal(
  model: PlayoffBracketModel,
  {forceShowAll = false}: BracketRevealOptions = {},
): BracketRevealState {
  const [state, setState] = useState<RevealState>({season: model.season, rounds: new Set()});
  const [statusMessage, setStatusMessage] = useState(HIDDEN_STATUS);
  const sortedRounds = useMemo(
    () => [...model.rounds].sort((a, b) => a.sortOrder - b.sortOrder),
    [model.rounds],
  );
  const revealedRounds = useMemo(
    () => forceShowAll
      ? new Set(sortedRounds.map(round => round.round))
      : state.season === model.season ? state.rounds : new Set<number>(),
    [forceShowAll, model.season, sortedRounds, state],
  );

  useEffect(() => {
    setState(previous => previous.season === model.season && !forceShowAll
      ? previous
      : {season: model.season, rounds: new Set()});
    setStatusMessage(forceShowAll ? "All playoff results are shown." : HIDDEN_STATUS);
  }, [forceShowAll, model.season]);

  const canRevealRound = useCallback((round: number) => (
    canRevealRoundFromModel(round, sortedRounds, revealedRounds)
  ), [revealedRounds, sortedRounds]);

  const revealRound = useCallback((round: number) => {
    if (forceShowAll) return;
    const roundIndex = sortedRounds.findIndex(item => item.round === round);
    if (roundIndex < 0 || !canRevealRoundFromModel(round, sortedRounds, revealedRounds)) return;

    setState(previous => {
      const previousRounds = previous.season === model.season ? previous.rounds : new Set<number>();
      return {season: model.season, rounds: new Set([...previousRounds, round])};
    });
    const current = sortedRounds[roundIndex];
    const next = sortedRounds[roundIndex + 1];
    setStatusMessage(next
      ? `${current.label} results revealed. ${next.label} is now unlocked.`
      : `${current.label} results revealed.`);
  }, [forceShowAll, model.season, revealedRounds, sortedRounds]);

  const hideRound = useCallback((round: number) => {
    if (forceShowAll) return;
    const roundIndex = sortedRounds.findIndex(item => item.round === round);
    if (roundIndex < 0) return;
    const hiddenRoundNumbers = new Set(sortedRounds.slice(roundIndex).map(item => item.round));

    setState(previous => {
      const next = new Set(previous.season === model.season ? previous.rounds : []);
      hiddenRoundNumbers.forEach(hiddenRound => next.delete(hiddenRound));
      return {season: model.season, rounds: next};
    });
    setStatusMessage(`${sortedRounds[roundIndex].label} and all later results are hidden.`);
  }, [forceShowAll, model.season, sortedRounds]);

  const revealThroughRound = useCallback((round: number) => {
    if (forceShowAll) return;
    const roundIndex = sortedRounds.findIndex(item => item.round === round);
    if (roundIndex < 0) return;
    const roundsToReveal = sortedRounds.slice(0, roundIndex + 1);

    setState(previous => {
      const next = new Set(previous.season === model.season ? previous.rounds : []);
      roundsToReveal.forEach(item => next.add(item.round));
      return {season: model.season, rounds: next};
    });
    setStatusMessage(`${sortedRounds[roundIndex].label} and required earlier results are shown.`);
  }, [forceShowAll, model.season, sortedRounds]);

  const hideAllResults = useCallback(() => {
    if (forceShowAll) return;
    setState({season: model.season, rounds: new Set()});
    setStatusMessage("All playoff results are hidden.");
  }, [forceShowAll, model.season]);

  const showAllResults = useCallback(() => {
    if (forceShowAll) return;
    setState({season: model.season, rounds: new Set(sortedRounds.map(round => round.round))});
    setStatusMessage("All playoff results are shown.");
  }, [forceShowAll, model.season, sortedRounds]);

  return {
    revealedRounds,
    statusMessage,
    canRevealRound,
    revealRound,
    revealThroughRound,
    hideRound,
    showAllResults,
    hideAllResults,
  };
}

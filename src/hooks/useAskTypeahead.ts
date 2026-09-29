import {useEffect, useMemo, useState} from "react";
import {useQuery} from "@tanstack/react-query";
import {buildTypeaheadGroups, normalizeAskQuery, type AskActionGroup} from "@/components/ask/askTypeahead";
import {ASK_SUGGEST_MAX_LENGTH, getAskSuggestions} from "@/services/ask/askService";

export const TYPEAHEAD_DEBOUNCE_MS = 200;
export const TYPEAHEAD_MIN_LENGTH = 2;
const SUGGEST_STALE_MS = 5 * 60 * 1000;

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

interface AskTypeaheadOptions {
  query: string;
  resultsHidden: boolean;
  enabled: boolean;
}

/**
 * Grouped typeahead. Lookups go to GET /ask/suggest, which never calls a model; they are debounced,
 * skipped for very short or long text, and cached per normalized text and hidden state.
 */
export function useAskTypeahead({query, resultsHidden, enabled}: AskTypeaheadOptions) {
  const debounced = normalizeAskQuery(useDebouncedValue(query, TYPEAHEAD_DEBOUNCE_MS));
  const canLookUp = enabled && debounced.length >= TYPEAHEAD_MIN_LENGTH && debounced.length <= ASK_SUGGEST_MAX_LENGTH;

  const suggestQuery = useQuery({
    queryKey: ["ask", "suggest", debounced, resultsHidden],
    queryFn: ({signal}) => getAskSuggestions(debounced, resultsHidden, signal),
    enabled: canLookUp,
    staleTime: SUGGEST_STALE_MS,
    retry: false,
  });

  // Only use suggestions for the text currently in the field, so the rows never lag what Enter runs.
  const current = normalizeAskQuery(query);
  const suggest = canLookUp && debounced === current ? suggestQuery.data : undefined;
  const groups: AskActionGroup[] = useMemo(
    () => buildTypeaheadGroups({query, suggest, resultsHidden}),
    [query, suggest, resultsHidden],
  );

  return {groups, isLookingUp: suggestQuery.isFetching};
}

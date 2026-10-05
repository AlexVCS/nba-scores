import {useSyncExternalStore} from "react";
import {getAskSessionSnapshot, subscribeAskSession, type AskSessionState} from "@/components/ask/askSessionStore";

export function useAskSession(): AskSessionState {
  return useSyncExternalStore(subscribeAskSession, getAskSessionSnapshot, getAskSessionSnapshot);
}

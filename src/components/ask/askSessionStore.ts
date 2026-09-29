// In-memory Ask session. Lives outside React so closing the dialog or moving between pages keeps the
// current question and answer. Nothing here is persisted.
import {postAsk} from "@/services/ask/askService";
import type {AskClientContext, AskQuery, AskResponse} from "@/services/ask/types";

export type AskRequester = (query: AskQuery, signal: AbortSignal) => Promise<AskResponse>;

export interface AskSubmission {
  id: number;
  question: string;
  resolution: string | null;
  context: AskClientContext | null;
}

export interface AskSessionState {
  query: string;
  submission: AskSubmission | null;
  status: "idle" | "loading" | "success" | "error";
  response: AskResponse | null;
}

const INITIAL_STATE: AskSessionState = {
  query: "",
  submission: null,
  status: "idle",
  response: null,
};

let state = INITIAL_STATE;
let nextId = 1;
let controller: AbortController | null = null;
let requester: AskRequester = postAsk;
const listeners = new Set<() => void>();

function setState(patch: Partial<AskSessionState>) {
  state = {...state, ...patch};
  listeners.forEach(listener => listener());
}

export function subscribeAskSession(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export const getAskSessionSnapshot = () => state;

export const askSession = {
  setQuery(query: string) {
    setState({query});
  },

  /**
   * Sends a question. The server stamps its own reference time, so re-running "last week" resolves
   * against the new request time. A clarification `resolution` token executes without a model call.
   */
  submit(question: string, {resolution = null, context = null}: {resolution?: string | null; context?: AskClientContext | null} = {}) {
    const trimmed = question.trim();
    if (!trimmed) return;
    controller?.abort();
    const abort = new AbortController();
    controller = abort;
    const submission: AskSubmission = {id: nextId++, question: trimmed, resolution, context};
    setState({query: trimmed, submission, status: "loading", response: null});

    requester({question: trimmed, context, resolution}, abort.signal)
      .then(response => {
        if (state.submission?.id !== submission.id) return;
        setState({status: "success", response});
      })
      .catch(() => {
        if (abort.signal.aborted || state.submission?.id !== submission.id) return;
        setState({status: "error"});
      });
  },

  retry() {
    const current = state.submission;
    if (current) askSession.submit(current.question, {resolution: current.resolution, context: current.context});
  },

  /** Test seam: swap the transport. */
  setRequester(next: AskRequester) {
    requester = next;
  },

  reset() {
    controller?.abort();
    controller = null;
    requester = postAsk;
    state = INITIAL_STATE;
    listeners.forEach(listener => listener());
  },
};

import {act, render, screen, waitFor, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {ASK_RESPONSE_FIXTURES, ASK_SUGGEST_FIXTURES} from "@/services/ask/fixtures";
import {ASK_RECENT_STORAGE_KEY} from "@/services/ask/recentSearches";
import type {AskQuery, AskResponse} from "@/services/ask/types";
import AskEntry from "./AskEntry";
import {askSession} from "./askSessionStore";
import {AskTestProviders} from "./askTestUtils";

function setup(path?: string) {
  const user = userEvent.setup();
  render(<AskTestProviders path={path}><AskEntry /></AskTestProviders>);
  return user;
}

function mockRequester(response: AskResponse | ((query: AskQuery) => AskResponse)) {
  const requester = vi.fn(async (query: AskQuery) => typeof response === "function" ? response(query) : response);
  askSession.setRequester(requester);
  return requester;
}

const input = () => screen.getByRole("combobox", {name: "Ask a question"});
const options = () => within(screen.getByRole("listbox")).getAllByRole("option");
const selectedOption = () => options().find(option => option.getAttribute("aria-selected") === "true");

describe("Ask entry and search dialog", () => {
  beforeEach(() => {
    localStorage.clear();
    askSession.reset();
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (String(url).includes("/ask/suggest")) return new Response(JSON.stringify(ASK_SUGGEST_FIXTURES["knicks-hidden"]));
      return new Response("{}", {status: 404});
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    act(() => askSession.reset());
  });

  it("opens from the header button, focuses the field, and restores focus on Escape", async () => {
    const user = setup();
    const trigger = screen.getByRole("button", {name: "Ask about a game, stat, or series"});

    await user.click(trigger);
    expect(screen.getByRole("dialog", {name: "Ask"})).toBeInTheDocument();
    await waitFor(() => expect(input()).toHaveFocus());

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("opens with Ctrl+K or Cmd+K from anywhere, and with / outside text fields", async () => {
    const user = setup();
    await user.keyboard("{Control>}k{/Control}");
    expect(screen.getByRole("dialog", {name: "Ask"})).toBeInTheDocument();
    await user.keyboard("{Escape}");

    await user.keyboard("{Meta>}k{/Meta}");
    expect(screen.getByRole("dialog", {name: "Ask"})).toBeInTheDocument();
    await user.keyboard("{Escape}");

    await user.keyboard("/");
    expect(screen.getByRole("dialog", {name: "Ask"})).toBeInTheDocument();
  });

  it("puts direct game matches before Ask rows for a short entity query, and Enter opens the selected game", async () => {
    const user = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(input(), "knicks");

    await waitFor(() => expect(screen.getByRole("group", {name: "Games"})).toBeInTheDocument());
    const groups = within(screen.getByRole("listbox")).getAllByRole("group").map(group => group.getAttribute("aria-labelledby") && group.textContent);
    expect(groups[0]).toMatch(/^Games/);
    expect(selectedOption()).toHaveTextContent("NYK @ BOS");
    expect(input()).toHaveAttribute("aria-activedescendant", selectedOption()!.id);

    await user.keyboard("{Enter}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/design-1/games/0022500801/boxscore?date=2026-02-08");
  });

  it("selects the Ask row first for question-shaped text; arrows move the selection and Enter runs it", async () => {
    const requester = mockRequester(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    const user = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(input(), "how many points did harden score on march 9 2026");

    expect(selectedOption()).toHaveTextContent("Ask “how many points did harden score on march 9 2026”");
    await user.keyboard("{Enter}");

    expect(requester).toHaveBeenCalledTimes(1);
    expect(requester.mock.calls[0][0]).toMatchObject({
      question: "how many points did harden score on march 9 2026",
      resolution: null,
      context: {route: "scores", view_date: "2026-02-05"},
    });
    await waitFor(() => expect(screen.getByRole("region", {name: "How Ask read your question"})).toBeInTheDocument());
  });

  it("does not call the Ask endpoint while typing", async () => {
    const requester = mockRequester(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    const user = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(input(), "who won the 2024 finals");
    expect(requester).not.toHaveBeenCalled();
    const calls = vi.mocked(fetch).mock.calls.map(([url]) => String(url));
    expect(calls.every(url => url.includes("/ask/suggest"))).toBe(true);
  });

  it("stores only the question in size-limited recent history, and clears it", async () => {
    mockRequester(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    const user = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(input(), "how many points did harden score on march 9 2026{Enter}");
    await waitFor(() => expect(screen.getByRole("button", {name: "Reveal points"})).toBeInTheDocument());

    const stored = JSON.parse(localStorage.getItem(ASK_RECENT_STORAGE_KEY)!);
    expect(stored).toEqual([{question: "how many points did harden score on march 9 2026", askedAt: expect.any(String)}]);
    await user.click(screen.getByRole("button", {name: "Reveal points"}));
    expect(localStorage.getItem(ASK_RECENT_STORAGE_KEY)).not.toMatch(/21|104|112/);

    await user.click(screen.getByRole("button", {name: "Clear question"}));
    expect(input()).toHaveValue("");
    expect(input()).toHaveFocus();
    expect(screen.getByRole("group", {name: "Recent"})).toHaveTextContent("how many points did harden");

    await user.keyboard("{ArrowDown}");
    expect(selectedOption()).toHaveTextContent("how many points did harden");

    await user.click(screen.getByRole("button", {name: "Clear recent searches"}));
    expect(screen.queryByRole("group", {name: "Recent"})).not.toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(ASK_RECENT_STORAGE_KEY)!)).toEqual([]);
  });

  it("keeps digits in the search field while it is focused, and uses them to pick a clarification outside it", async () => {
    const requester = mockRequester(query => query.resolution
      ? ASK_RESPONSE_FIXTURES["answer-player-stat"]
      : ASK_RESPONSE_FIXTURES["clarification-which-jalen"]);
    const user = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(input(), "how did jalen do last night{Enter}");
    await waitFor(() => expect(screen.getByRole("heading", {name: "Which Jalen?"})).toBeInTheDocument());

    await user.type(input(), " 2");
    expect(input()).toHaveValue("how did jalen do last night 2");
    expect(requester).toHaveBeenCalledTimes(1);

    await user.clear(input());
    await user.type(input(), "how did jalen do last night{Enter}");
    await waitFor(() => expect(screen.getByRole("heading", {name: "Which Jalen?"})).toBeInTheDocument());
    await user.click(screen.getByRole("heading", {name: "Which Jalen?"}));
    await user.keyboard("2");

    expect(requester).toHaveBeenLastCalledWith(
      expect.objectContaining({question: "How did Jalen Suggs do on February 5, 2026?", resolution: "rsv_fx_jalen_2"}),
      expect.anything(),
    );
    expect(input()).toHaveValue("How did Jalen Suggs do on February 5, 2026?");
  });

  it("resets local reveals on a new question but keeps them when the dialog closes and reopens", async () => {
    mockRequester(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    const user = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(input(), "how many points did harden score on march 9 2026{Enter}");
    await user.click(await screen.findByRole("button", {name: "Reveal points"}));
    expect(screen.getByRole("button", {name: "Hide points"})).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await user.keyboard("{Control>}k{/Control}");
    expect(input()).toHaveValue("how many points did harden score on march 9 2026");
    expect(screen.getByRole("button", {name: "Hide points"})).toBeInTheDocument();

    await user.clear(input());
    await user.type(input(), "how many points did harden score on march 10 2026{Enter}");
    expect(await screen.findByRole("button", {name: "Reveal points"})).toBeInTheDocument();
  });

  it("shows a retry state when Ask cannot be reached", async () => {
    let fail = true;
    askSession.setRequester(vi.fn(async () => {
      if (fail) throw new Error("offline");
      return ASK_RESPONSE_FIXTURES["answer-player-stat"];
    }));
    const user = setup();
    await user.keyboard("{Control>}k{/Control}");
    await user.type(input(), "how many points did harden score on march 9 2026{Enter}");
    expect(await screen.findByRole("heading", {name: "Couldn’t reach Ask"})).toBeInTheDocument();

    fail = false;
    await user.click(screen.getByRole("button", {name: "Try again"}));
    expect(await screen.findByRole("button", {name: "Reveal points"})).toBeInTheDocument();
  });
});

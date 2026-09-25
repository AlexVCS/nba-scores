import {act, cleanup, fireEvent, render, within} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {ResultsVisibilityContext} from "@/context/ResultsVisibilityContext";
import type {PlayoffBracketResponse, SeriesData} from "@/helpers/helpers";
import Design1PlayoffBracket from "./Design1PlayoffBracket";

let viewportWidth = 1600;
const mediaQueries = new Set<{dispatchEvent: (event: Event) => boolean; matches: boolean; media: string}>();

function resizeViewport(width: number) {
  act(() => {
    viewportWidth = width;
    mediaQueries.forEach(query => query.dispatchEvent(new Event("change")));
  });
}

function makeBracket(exact = false): PlayoffBracketResponse {
  const rounds = [
    {round: 10, label: "Opening Round", sortOrder: 1, defaultRevealed: false},
    {round: 30, label: "Division Finals", sortOrder: 2, defaultRevealed: false},
    {round: 50, label: "NBA Finals", sortOrder: 3, defaultRevealed: false},
  ];
  const series: SeriesData[] = rounds.flatMap(round => (round.round === 50 ? ["finals"] : ["west", "east"]).map(group => ({
    seriesKey: `${group}-${round.round}`,
    round: round.round,
    roundName: round.label,
    bracketGroupId: group,
    bracketGroupKind: group === "finals" ? "finals" : exact ? "conference" : "division",
    teams: [{id: 1610612738, tricode: "BOS", name: "Celtics"}, {id: 1610612752, tricode: "NYK", name: "Knicks"}],
    wins: {1610612738: 4, 1610612752: 2},
    winnerTeamId: 1610612738,
    winnerTeamTricode: "BOS",
    gameCount: 6,
    games: [],
    targetWins: 4,
  })));
  return {
    season: exact ? "2024-25" : "1953-54",
    teamGameRowCount: 60,
    gameCount: 30,
    seriesCount: series.length,
    format: {
      era: exact ? "modern-play-in-era" : "six-team-round-robin",
      playoffYear: exact ? 2025 : 1954,
      finalsRound: 50,
      bracketType: exact ? "single-elimination" : "round-robin-plus-finals",
      supportsExactBracket: exact,
      notes: [],
    },
    groups: [
      {id: "west", label: "West", kind: exact ? "conference" : "division", sortOrder: 1},
      {id: "east", label: "East", kind: exact ? "conference" : "division", sortOrder: 2},
      {id: "finals", label: "NBA Finals", kind: "finals", sortOrder: 3},
    ],
    rounds,
    edges: [],
    series,
  };
}

function renderBracket(exact = false, showAllResults = false, playoffPicture = makeBracket(exact)) {
  const content = (picture: PlayoffBracketResponse) => (
    <MemoryRouter>
      <ResultsVisibilityContext.Provider value={{showAllResults, setShowAllResults: vi.fn(), toggleShowAllResults: vi.fn(), isSpoilerHintDismissed: true, dismissSpoilerHint: vi.fn()}}>
        <Design1PlayoffBracket playoffPicture={picture} />
      </ResultsVisibilityContext.Provider>
    </MemoryRouter>
  );
  const view = render(content(playoffPicture));
  const desktopElement = () => view.container.querySelector<HTMLElement>('[class^="hidden min-["]')!;
  return {
    ...view,
    rerenderBracket: (picture: PlayoffBracketResponse) => view.rerender(content(picture)),
    get desktop() { return within(desktopElement()); },
    get desktopElement() { return desktopElement(); },
    mobile: within(view.container.querySelector<HTMLElement>(".mobile-bracket")!),
  };
}

beforeEach(() => {
  viewportWidth = 1600;
  mediaQueries.clear();
  vi.stubGlobal("matchMedia", (media: string) => {
    const target = new EventTarget();
    const query = {
      media,
      get matches() { return viewportWidth >= Number(media.match(/\d+/)?.[0]); },
      addEventListener: target.addEventListener.bind(target),
      removeEventListener: target.removeEventListener.bind(target),
      dispatchEvent: target.dispatchEvent.bind(target),
    };
    mediaQueries.add(query);
    return query;
  });
  vi.stubGlobal("IntersectionObserver", class {
    observe() {}
    disconnect() {}
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("responsive desktop mounting", () => {
  it.each([false, true])("omits desktop cards and measurements on phones (exact: %s)", exact => {
    resizeViewport(390);
    const observer = vi.fn();
    vi.stubGlobal("ResizeObserver", class {
      constructor() { observer(); }
      observe() {}
      disconnect() {}
    });
    const {container, desktopElement, mobile} = renderBracket(exact);
    expect(desktopElement).toBeNull();
    expect(container.querySelector(".hw-bracket-measure")).toBeNull();
    expect(observer).not.toHaveBeenCalled();
    expect(mobile.getByRole("region", {name: "Opening Round"})).toBeInTheDocument();
  });

  it.each([false, true])("uses the existing breakpoint (compact: %s)", compact => {
    const bracket = makeBracket(!compact);
    if (compact) bracket.series = bracket.series.filter(series => series.round !== 30);
    const breakpoint = compact ? 1100 : 1440;
    resizeViewport(breakpoint - 1);
    const view = renderBracket(!compact, false, bracket);
    expect(view.desktopElement).toBeNull();
    resizeViewport(breakpoint);
    expect(view.desktopElement).toBeInTheDocument();
    expect(view.desktopElement.className).toBe(`hidden min-[${breakpoint}px]:block`);
    resizeViewport(breakpoint - 1);
    expect(view.desktopElement).toBeNull();
  });

  it("preserves reveals and mobile navigation while measuring each desktop mount", () => {
    resizeViewport(390);
    const observers: {observe: ReturnType<typeof vi.fn>; disconnect: ReturnType<typeof vi.fn>}[] = [];
    vi.stubGlobal("ResizeObserver", class {
      observe = vi.fn();
      disconnect = vi.fn();
      constructor() { observers.push(this); }
    });
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({height: 180} as DOMRect);
    const view = renderBracket(true);
    const opening = within(view.mobile.getByRole("region", {name: "Opening Round"}));
    fireEvent.click(opening.getByRole("button", {name: "Show results"}));
    const mobileElement = view.container.querySelector(".mobile-bracket");
    expect(observers).toHaveLength(0);

    for (let mount = 0; mount < 2; mount++) {
      resizeViewport(1440);
      expect(view.desktop.getAllByRole("button", {name: "Hide Opening Round and later round results"})).toHaveLength(2);
      expect(view.desktopElement.style.getPropertyValue("--hw-bracket-card-height")).toBe("180px");
      expect(view.desktopElement.style.getPropertyValue("--hw-bracket-finals-height")).toBe("180px");
      expect(observers).toHaveLength(mount + 1);
      expect(observers[mount].observe).toHaveBeenCalled();
      resizeViewport(390);
      expect(observers[mount].disconnect).toHaveBeenCalledOnce();
      expect(view.desktopElement).toBeNull();
      expect(view.container.querySelector(".mobile-bracket")).toBe(mobileElement);
      expect(opening.getByRole("button", {name: "Hide results"})).toBeInTheDocument();
    }
  });

  it("keeps globally shown results across breakpoint crossings", () => {
    resizeViewport(390);
    const view = renderBracket(true, true);
    resizeViewport(1440);
    expect(view.desktop.queryByRole("button")).not.toBeInTheDocument();
    expect(view.desktop.getAllByRole("link", {name: "Celtics 4, Knicks 2. View series details."})).toHaveLength(5);
    resizeViewport(390);
    expect(within(view.mobile.getByRole("region", {name: "NBA Finals"})).getByRole("link")).toHaveAccessibleName("Celtics 4, Knicks 2. View series details.");
  });

  it("switches breakpoints immediately when changing season and resets revealed results", () => {
    resizeViewport(1200);
    const compact = makeBracket();
    compact.series = compact.series.filter(series => series.round !== 30);
    const view = renderBracket(false, false, compact);
    fireEvent.click(view.desktop.getByRole("button", {name: "Show all results"}));
    expect(view.desktop.getByRole("button", {name: "Hide all results"})).toBeInTheDocument();

    view.rerenderBracket(makeBracket(true));
    expect(view.desktopElement).toBeNull();
    expect(within(view.mobile.getByRole("region", {name: "Opening Round"})).getByRole("button", {name: "Show results"})).toBeInTheDocument();
    resizeViewport(1440);
    expect(view.desktop.getByLabelText("NBA Finals locked until Division Finals is revealed")).toBeInTheDocument();
    resizeViewport(1200);
    view.rerenderBracket(compact);
    expect(view.desktopElement).toBeInTheDocument();
    expect(view.desktop.getByRole("button", {name: "Show all results"})).toBeInTheDocument();
  });
});

describe("Design1PlayoffBracket Finals controls", () => {
  it("removes absent group rounds while retaining recorded locked rounds", () => {
    const bracket = makeBracket(true);
    bracket.series = bracket.series.filter(series => series.seriesKey !== "east-10");
    const {desktop, desktopElement} = renderBracket(true, false, bracket);
    expect(desktop.getAllByRole("heading", {name: "Opening Round"})).toHaveLength(1);
    expect(desktop.getAllByRole("heading", {name: "Division Finals"})).toHaveLength(2);
    expect(desktop.queryByText("No recorded matchup")).not.toBeInTheDocument();
    expect(desktopElement.querySelectorAll(".hw-bracket-round--exact")).toHaveLength(4);
    expect(desktopElement.querySelector<HTMLElement>('[style*="grid-template-columns"]')?.style.gridTemplateColumns).toBe("repeat(4, minmax(0, var(--hw-bracket-column-width)))");
    expect(desktop.getAllByLabelText("Division Finals locked until Opening Round is revealed")).toHaveLength(2);
  });

  it.each([false, true])("reveals and hides Finals independently in the desktop bracket (exact: %s)", exact => {
    const {desktop, desktopElement} = renderBracket(exact);
    expect(desktopElement.querySelector(".hw-bracket-round--exact") !== null).toBe(exact);
    expect(desktop.getByLabelText("NBA Finals locked until Division Finals is revealed")).toBeInTheDocument();
    expect(desktop.queryByRole("button", {name: "Reveal NBA Finals results"})).not.toBeInTheDocument();

    fireEvent.click(desktop.getAllByRole("button", {name: "Reveal Opening Round results"})[0]);
    expect(desktop.getByLabelText("NBA Finals locked until Division Finals is revealed")).toBeInTheDocument();
    fireEvent.click(desktop.getAllByRole("button", {name: "Reveal Division Finals results"})[0]);

    const finals = within(desktop.getAllByRole("region", {name: "NBA Finals"}).slice(-1)[0]);
    expect(finals.getByRole("link", {name: "Celtics versus Knicks. View series details."})).toBeInTheDocument();
    fireEvent.click(desktop.getByRole("button", {name: "Reveal NBA Finals results"}));
    expect(finals.getByRole("link", {name: "Celtics 4, Knicks 2. View series details."})).toBeInTheDocument();
    fireEvent.click(desktop.getByRole("button", {name: "Hide NBA Finals and later round results"}));
    expect(finals.getByRole("link", {name: "Celtics versus Knicks. View series details."})).toBeInTheDocument();
    expect(desktop.getAllByRole("button", {name: "Hide Division Finals and later round results"})).toHaveLength(2);
    expect(desktop.getAllByRole("link", {name: "Celtics 4, Knicks 2. View series details."})).toHaveLength(4);

    fireEvent.click(desktop.getByRole("button", {name: "Reveal NBA Finals results"}));
    fireEvent.click(desktop.getAllByRole("button", {name: "Hide Division Finals and later round results"})[0]);
    expect(desktop.getByLabelText("NBA Finals locked until Division Finals is revealed")).toBeInTheDocument();
    expect(finals.queryByRole("link")).not.toBeInTheDocument();
    expect(desktop.getAllByRole("button", {name: "Hide Opening Round and later round results"})).toHaveLength(2);
  });

  it.each([false, true])("suppresses individual Finals controls when results are globally shown (exact: %s)", exact => {
    const {desktop, mobile} = renderBracket(exact, true);
    const finals = within(desktop.getAllByRole("region", {name: "NBA Finals"}).slice(-1)[0]);
    expect(finals.getByRole("link", {name: "Celtics 4, Knicks 2. View series details."})).toBeInTheDocument();
    expect(desktop.queryByRole("button")).not.toBeInTheDocument();
    expect(desktop.queryByLabelText(/NBA Finals locked/)).not.toBeInTheDocument();
    expect(within(mobile.getByRole("region", {name: "NBA Finals"})).queryByRole("button")).not.toBeInTheDocument();
  });

  it("keeps mobile Finals reveal and hide controls working", () => {
    const {mobile} = renderBracket();
    for (const name of ["Opening Round", "Division Finals"]) {
      fireEvent.click(within(mobile.getByRole("region", {name})).getByRole("button", {name: "Show results"}));
    }
    const finals = within(mobile.getByRole("region", {name: "NBA Finals"}));
    fireEvent.click(finals.getByRole("button", {name: "Show results"}));
    expect(finals.getByRole("link", {name: "Celtics 4, Knicks 2. View series details."})).toBeInTheDocument();
    fireEvent.click(finals.getByRole("button", {name: "Hide results"}));
    expect(finals.getByRole("link", {name: "Celtics versus Knicks. View series details."})).toBeInTheDocument();
    expect(within(mobile.getByRole("region", {name: "Division Finals"})).getByRole("button", {name: "Hide results"})).toBeInTheDocument();
  });
});


describe("historical round names", () => {
  it.each([false, true])("uses BAA metadata in desktop and mobile headings, locked states and announcements (exact: %s)", exact => {
    const bracket = makeBracket(exact);
    bracket.season = "1948-49";
    bracket.rounds![0].label = "Division Semifinals";
    bracket.rounds![2].label = "BAA Finals";
    bracket.groups!.find(group => group.kind === "finals")!.label = "BAA Finals";
    const {desktop, mobile, container} = renderBracket(exact, false, bracket);

    expect(desktop.getAllByRole("heading", {name: "BAA Finals"}).length).toBeGreaterThan(0);
    expect(mobile.getByRole("region", {name: "BAA Finals"})).toBeInTheDocument();
    expect(within(mobile.getByRole("region", {name: "BAA Finals"})).getByRole("heading", {level: 3, name: "BAA Finals"})).toBeInTheDocument();
    expect(desktop.getByLabelText("BAA Finals locked until Division Finals is revealed")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("NBA Finals");
    fireEvent.click(desktop.getAllByRole("button", {name: "Reveal Division Semifinals results"})[0]);
    expect(within(container).getByRole("status")).toHaveTextContent("Division Semifinals results revealed.");
    fireEvent.click(desktop.getAllByRole("button", {name: "Reveal Division Finals results"})[0]);
    fireEvent.click(desktop.getByRole("button", {name: "Reveal BAA Finals results"}));
    expect(within(container).getByRole("status")).toHaveTextContent("BAA Finals results revealed.");
  });
});

import {fireEvent, render, screen, within} from "@testing-library/react";
import {MemoryRouter} from "react-router";
import {beforeEach, describe, expect, it} from "vitest";
import type {AskItem} from "@/helpers/ask";
import {ResultsVisibilityProvider} from "@/providers/ResultsVisibilityProvider";
import AskAnswerCard from "./AskAnswerCard";

const player: AskItem = {
  kind: "statistic", title: "Jayson Tatum", title_spoiler: true,
  fields: [{label: "Points", value: 31, spoiler: true}],
  links: [], player_id: 1628369,
  teams: [{id: 1610612738, tricode: "BOS", name: "Boston Celtics"}],
  context: "Game 5 · 2024 NBA Finals",
};

function show(item: AskItem, interpretation: string[] = [], route = "/design-1") {
  render(<MemoryRouter initialEntries={[route]}><ResultsVisibilityProvider><ul>
    <AskAnswerCard item={item} interpretation={interpretation} makePath={path => `/design-1${path}`} />
  </ul></ResultsVisibilityProvider></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", {name: "Reveal result"}));
}

describe("Ask answer presentation", () => {
  beforeEach(() => localStorage.clear());

  it.each(["/design-1", "/original"])("uses the existing game card and its links on %s", route => {
    show({kind: "game", title: "NBA game", title_spoiler: false,
      fields: [{label: "Date", value: "2024-01-02", spoiler: false}], links: [],
      game: {
        gameId: "0022300464", gameCode: "20240102/BOSOKC", gameStatus: 3,
        gameStatusText: "Final", gameLabel: "", gameSubLabel: "", gameTimeUTC: "2024-01-03T01:00:00Z",
        ifNecessary: false, seriesGameNumber: "", seriesText: "",
        awayTeam: {teamId: 1610612738, teamTricode: "BOS", teamName: "Celtics", score: 123},
        homeTeam: {teamId: 1610612760, teamTricode: "OKC", teamName: "Thunder", score: 127},
      },
    }, ["Thunder", "January 2, 2024"], route);
    expect(screen.getByRole("article")).toBeInTheDocument();
    expect(screen.getByRole("link", {name: "View BOS at OKC game details"})).toHaveAttribute("href", `${route}/games/0022300464/boxscore?date=2024-01-02`);
    expect(screen.getByRole("link", {name: /Watch/i})).toHaveAttribute("target", "_blank");
    expect(screen.getAllByText("123")).toHaveLength(1);
    expect(screen.getAllByText("127")).toHaveLength(1);
    expect(screen.getByText("BOS")).toBeInTheDocument();
    expect(screen.getByText("OKC")).toBeInTheDocument();
    const interpretation = screen.getByText("Interpreted as:").parentElement;
    expect(screen.getByRole("article").compareDocumentPosition(interpretation!)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    fireEvent.click(screen.getByRole("button", {name: "Hide result"}));
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("January 2, 2024")).toBeInTheDocument();
  });

  it("puts multiple requested values in the table without repeating them in the headline", () => {
    show({...player, fields: [...player.fields, {label: "Assists", value: 11, spoiler: true}]});
    const heading = screen.getByRole("heading");
    expect(heading).toHaveTextContent("Jayson Tatum");
    expect(heading).not.toHaveTextContent("31");
    expect(heading).not.toHaveTextContent("11");
    const table = screen.getByRole("table");
    expect(within(table).getByRole("cell", {name: "31"})).toBeInTheDocument();
    expect(within(table).getByRole("cell", {name: "11"})).toBeInTheDocument();
  });

  it("distinguishes a leader answer from a player stat", () => {
    show(player, ["Game leaders", "Points"]);
    expect(screen.getByRole("heading")).toHaveTextContent("Jayson Tatum led the game with 31 points");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("does not infer that a historical series is in progress when its winner is missing", () => {
    show({kind: "series", title: "1950 NBA Finals", title_spoiler: true,
      fields: [{label: "Team 1", value: "Lakers", spoiler: true}, {label: "Team 2", value: "Nationals", spoiler: true}], links: []});
    expect(screen.getByRole("heading")).not.toHaveTextContent(/in progress|beat|4–0/i);
  });

  it("preserves a known winner without inventing team identities from absent metadata", () => {
    show({kind: "series", title: "NBA Finals", title_spoiler: true,
      fields: [{label: "Series winner", value: "BOS", spoiler: true}], links: []});
    expect(screen.getByRole("heading")).toHaveTextContent("BOS");
    expect(screen.getByRole("heading")).not.toHaveTextContent("Team beat Team");
  });
});

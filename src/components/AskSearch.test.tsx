import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AskResponse } from "@/helpers/ask";
import { useResultsVisibility } from "@/hooks/useResultsVisibility";
import { ResultsVisibilityProvider } from "@/providers/ResultsVisibilityProvider";
import { askQuestion } from "@/services/nbaService";
import AskSearch from "./AskSearch";

vi.mock("@/services/nbaService", () => ({ askQuestion: vi.fn() }));

const response: AskResponse = {
  status: "ok",
  interpretation: ["Tatum", "Points", "2024 NBA Finals", "Game 5"],
  items: [
    {
      kind: "statistic",
      title: "Jayson Tatum",
      title_spoiler: true,
      fields: [{ label: "Points", value: 31, spoiler: true }],
      links: [
        {
          label: "Game details",
          path: "/games/0042300405/boxscore?date=2024-06-17",
          spoiler: true,
        },
      ],
      context: "Game 5 · 2024 NBA Finals",
      teams: [{ id: 1610612738, tricode: "BOS", name: "Boston Celtics" }],
      player_id: 1628369,
    },
  ],
};

function GlobalToggle() {
  const { toggleShowAllResults } = useResultsVisibility();
  return <button onClick={toggleShowAllResults}>Toggle global results</button>;
}

function setup() {
  render(
    <MemoryRouter initialEntries={["/design-1"]}>
      <ResultsVisibilityProvider>
        <GlobalToggle />
        <AskSearch />
      </ResultsVisibilityProvider>
    </MemoryRouter>,
  );
}

async function search() {
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "Who led Boston in game 5 of the 2024 Finals?" },
  });
  fireEvent.submit(screen.getByRole("search"));
  await screen.findByRole("button", { name: "Reveal result" });
}

describe("basketball search", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(askQuestion).mockResolvedValue(response);
  });

  it("is always visible and example chips submit immediately", async () => {
    setup();
    expect(screen.getByRole("searchbox")).toHaveAttribute(
      "placeholder",
      "Ask about a game, a stat, or a playoff series…",
    );
    fireEvent.click(screen.getByRole("button", { name: "2023 NBA Finals" }));
    await waitFor(() =>
      expect(askQuestion).toHaveBeenCalledWith(
        "Who won the 2023 NBA Finals?",
        expect.any(AbortSignal),
      ),
    );
    expect(
      screen.queryByRole("list", { name: "Example questions" }),
    ).not.toBeInTheDocument();
  });

  it("omits every spoiler value and identity asset until reveal", async () => {
    setup();
    await search();
    expect(screen.getByText("Tatum")).toBeInTheDocument();
    expect(screen.queryByText(/Jayson Tatum scored/)).not.toBeInTheDocument();
    expect(screen.queryByText("31")).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    const card = screen
      .getByRole("button", { name: "Reveal result" })
      .closest("li");
    expect(card).not.toHaveAttribute("style");

    fireEvent.click(screen.getByRole("button", { name: "Reveal result" }));
    expect(
      screen.getByRole("heading", {
        name: "Jayson Tatum scored 31 points in Game 5 of the 2024 NBA Finals.",
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/31 points/)).toHaveLength(1);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByAltText("Jayson Tatum headshot")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Game details/ })).toHaveAttribute(
      "href",
      "/design-1/games/0042300405/boxscore?date=2024-06-17",
    );
  });

  it("resets local reveal on a new search and after a global reveal cycle", async () => {
    setup();
    await search();
    fireEvent.click(screen.getByRole("button", { name: "Reveal result" }));
    await search();
    expect(screen.queryByText("31")).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Toggle global results" }),
    );
    expect(screen.getByText(/31 points/)).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Toggle global results" }),
    );
    expect(screen.queryByText("31")).not.toBeInTheDocument();
  });

  it("renders clarification with interpretation and useful examples", async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      status: "needs_clarification",
      message: "Which playoff year do you mean?",
      interpretation: ["Finals", "[which year?]"],
      items: [],
    });
    setup();
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "Show the Finals" },
    });
    fireEvent.submit(screen.getByRole("search"));
    expect(
      await screen.findAllByText("Which playoff year do you mean?"),
    ).toHaveLength(2);
    expect(screen.getByText("[which year?]")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Tatum, G5 of the 2024 Finals" }),
    ).toBeInTheDocument();
  });

  it("shows a card skeleton, then a recoverable error notice", async () => {
    let rejectRequest: (reason: Error) => void = () => undefined;
    vi.mocked(askQuestion).mockReturnValue(
      new Promise((_, reject) => {
        rejectRequest = reject;
      }),
    );
    setup();
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "Games yesterday" },
    });
    fireEvent.submit(screen.getByRole("search"));
    expect(screen.getByText("Searching basketball records")).toBeInTheDocument();
    rejectRequest(
      new Error("Search is unavailable right now. Please try again shortly."),
    );
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Search is unavailable",
      ),
    );
    expect(screen.getByRole("button", { name: "Search" })).toBeEnabled();
  });

  it("clearing the input restores examples and discards the result", async () => {
    setup();
    await search();
    fireEvent.click(screen.getByRole("button", {name: "Clear search"}));
    expect(screen.getByRole("searchbox")).toHaveValue("");
    expect(screen.getByRole("searchbox")).toHaveFocus();
    expect(screen.queryByRole("button", {name: "Clear search"})).not.toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: "Example questions" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Reveal result" }),
    ).not.toBeInTheDocument();
  });

  it("keeps a game interpretation visible while omitting the hidden matchup", async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      status: "ok",
      interpretation: ["Thunder", "Jan 2, 2024"],
      items: [
        {
          kind: "game",
          title: "NBA game",
          title_spoiler: false,
          fields: [
            { label: "Away", value: "BOS", spoiler: true },
            { label: "Home", value: "OKC", spoiler: true },
            { label: "Away score", value: 123, spoiler: true },
            { label: "Home score", value: 127, spoiler: true },
            { label: "Status", value: "Final", spoiler: true },
          ],
          links: [],
          teams: [
            { id: 1610612738, tricode: "BOS", name: "Boston Celtics" },
            { id: 1610612760, tricode: "OKC", name: "Oklahoma City Thunder" },
          ],
        },
      ],
    });
    setup();
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "Thunder on Jan 2, 2024" },
    });
    fireEvent.submit(screen.getByRole("search"));
    await screen.findByRole("button", { name: "Reveal result" });
    expect(screen.getByText("Thunder")).toBeInTheDocument();
    expect(screen.queryByText("Boston Celtics")).not.toBeInTheDocument();
    expect(screen.queryByText("127")).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("rejects external and unrelated result links", async () => {
    vi.mocked(askQuestion).mockResolvedValue({
      status: "ok",
      items: [
        {
          ...response.items[0],
          title_spoiler: false,
          fields: [],
          links: [
            { label: "External", path: "https://example.com", spoiler: false },
            {
              label: "Protocol relative",
              path: "//example.com",
              spoiler: false,
            },
            { label: "Unexpected", path: "/admin", spoiler: false },
          ],
        },
      ],
    });
    setup();
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "Games yesterday" },
    });
    fireEvent.submit(screen.getByRole("search"));
    await screen.findByText("Jayson Tatum in Game 5 of the 2024 NBA Finals.");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});

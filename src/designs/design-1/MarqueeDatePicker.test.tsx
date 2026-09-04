import {cleanup, fireEvent, render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {getLocalTimeZone, today} from "@internationalized/date";
import {MemoryRouter} from "react-router";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {useGameDays} from "@/hooks/useGameDays";
import MarqueeDatePicker from "./MarqueeDatePicker";

vi.mock("@/hooks/useGameDays");

beforeEach(() => {
  vi.stubGlobal("matchMedia", () => ({matches: false, addEventListener() {}, removeEventListener() {}}));
  vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
  vi.mocked(useGameDays).mockReturnValue({gameDays: new Set(), isLoading: false, error: new Error("Schedule unavailable"), season: undefined});
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function openPicker() {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/?date=2025-11-15"]}><MarqueeDatePicker /></MemoryRouter>);
  await user.click(screen.getByRole("button", {name: /Change date/}));
  return user;
}

async function enterDate(user: ReturnType<typeof userEvent.setup>, date: string) {
  const [year, month, day] = date.split("-");
  for (const [segment, value] of [["month", month], ["day", day], ["year", year]]) {
    await user.click(screen.getByRole("spinbutton", {name: new RegExp(segment, "i")}));
    await user.keyboard(value);
  }
  fireEvent.keyDown(screen.getByRole("spinbutton", {name: /year/i}), {key: "Enter"});
}

describe("MarqueeDatePicker date entry", () => {
  it.each(["1948-11-15", "2025-11-16", "1946-11-01", today(getLocalTimeZone()).add({years: 1}).toString()])(
    "navigates to in-range %s even when schedule lookup fails",
    async (date) => {
      const user = await openPicker();
      await enterDate(user, date);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      const [year, month, day] = date.split("-").map(Number);
      const label = new Date(year, month - 1, day).toLocaleDateString("en-US", {
        weekday: "long", month: "long", day: "numeric", year: "numeric",
      });
      expect(screen.getByRole("button", {name: `Change date — ${label}`})).toBeInTheDocument();
    },
  );

  it.each([
    ["1946-10-31", "This date is before the first NBA season."],
    [today(getLocalTimeZone()).add({years: 1, days: 1}).toString(), "No games available for this date yet."],
  ])("keeps out-of-range %s open with feedback", async (date, message) => {
    const user = await openPicker();
    await enterDate(user, date);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(message)).toBeInTheDocument();
  });

  it("shows feedback for an incomplete date", async () => {
    const user = await openPicker();
    await user.click(screen.getByRole("spinbutton", {name: /year/i}));
    await user.keyboard("{Backspace}{Backspace}{Backspace}{Backspace}");
    fireEvent.keyDown(screen.getByRole("spinbutton", {name: /year/i}), {key: "Enter"});
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Enter a complete date.")).toBeInTheDocument();
  });

  it("allows calendar selection when availability is unknown", async () => {
    const user = await openPicker();
    await user.click(screen.getByRole("button", {name: /Sunday, November 16, 2025/}));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Change date — Sunday, November 16, 2025"})).toBeInTheDocument();
  });
});

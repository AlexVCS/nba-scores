import {act, render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter} from "react-router";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {ThemeContext} from "@/context/ThemeContext";
import {ResultsVisibilityProvider, RESULTS_VISIBILITY_STORAGE_KEY, SPOILER_ONBOARDING_STORAGE_KEY} from "@/providers/ResultsVisibilityProvider";
import HardwoodHeader from "./HardwoodHeader";

type Section = "scores" | "playoffs" | "series" | "boxscore";

function header(section: Section = "scores", headerKey = "initial") {
  return (
    <MemoryRouter>
      <ThemeContext.Provider value={{theme: "light", toggleTheme: vi.fn()}}>
        <ResultsVisibilityProvider>
          <HardwoodHeader section={section} key={headerKey} />
        </ResultsVisibilityProvider>
      </ThemeContext.Provider>
    </MemoryRouter>
  );
}

describe("Hardwood spoiler onboarding", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it.each([
    ["scores", "Scorez"],
    ["playoffs", "Results"],
    ["series", "Scorez"],
    ["boxscore", "Scorez"],
  ] as const)("uses the right wording and global reveal action on %s", async (section, wording) => {
    const user = userEvent.setup();
    render(header(section));

    const control = screen.getByRole("button", {name: `${wording} hidden. Show all results`});
    const hint = screen.getByRole("region", {name: `${wording} start hidden`});
    const wrapper = hint.parentElement;
    expect(control).toHaveAttribute("aria-pressed", "false");
    expect(control).toHaveAttribute("aria-describedby", hint.id);
    expect(control).toHaveTextContent(`${wording} hidden`);
    expect(document.body).toHaveFocus();
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", {name: "Show all results"}));

    expect(screen.getByRole("button", {name: `${wording} shown. Hide all results`})).toBe(control);
    expect(control).toHaveAttribute("aria-pressed", "true");
    expect(control).toHaveFocus();
    expect(control).not.toHaveAttribute("aria-describedby");
    expect(hint).not.toBeInTheDocument();
    expect(wrapper).not.toBeInTheDocument();
    expect(control).toHaveTextContent(/^$/);
    expect(localStorage.getItem(RESULTS_VISIBILITY_STORAGE_KEY)).toBe("true");
    expect(localStorage.getItem(SPOILER_ONBOARDING_STORAGE_KEY)).toBe("true");
  });

  it("Got it removes its whole layout wrapper, keeps scores hidden, and remembers after reload", async () => {
    const user = userEvent.setup();
    const view = render(header());
    const control = screen.getByRole("button", {name: "Scorez hidden. Show all results"});
    const wrapper = screen.getByRole("region", {name: "Scorez start hidden"}).parentElement;
    const focus = vi.spyOn(control, "focus");

    await user.click(screen.getByRole("button", {name: "Got it"}));

    expect(wrapper).not.toBeInTheDocument();
    expect(control).toHaveTextContent(/^$/);
    expect(control).toHaveAttribute("aria-pressed", "false");
    expect(control).toHaveFocus();
    expect(focus).toHaveBeenCalledWith({preventScroll: true});
    expect(localStorage.getItem(RESULTS_VISIBILITY_STORAGE_KEY)).toBe("false");
    expect(localStorage.getItem(SPOILER_ONBOARDING_STORAGE_KEY)).toBe("true");
    focus.mockRestore();

    view.unmount();
    render(header());
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Scorez hidden. Show all results"})).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", {name: "Scorez hidden. Show all results"})).toHaveTextContent(/^$/);
  });

  it("direct control activation toggles globally and never reopens the hint", async () => {
    const user = userEvent.setup();
    const view = render(header());
    await user.click(screen.getByRole("button", {name: "Scorez hidden. Show all results"}));
    expect(screen.queryByRole("region")).not.toBeInTheDocument();

    view.rerender(header("playoffs", "bracket"));
    const bracketControl = screen.getByRole("button", {name: "Results shown. Hide all results"});
    expect(bracketControl).toHaveAttribute("aria-pressed", "true");
    expect(bracketControl).toHaveTextContent(/^$/);
    await user.click(bracketControl);
    expect(screen.getByRole("button", {name: "Results hidden. Show all results"})).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("region")).not.toBeInTheDocument();

    view.rerender(header("series", "series"));
    expect(screen.getByRole("button", {name: "Scorez hidden. Show all results"})).toBeInTheDocument();
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it("supports keyboard actions and Escape only while focus is inside the hint", async () => {
    const user = userEvent.setup();
    render(header());
    const control = screen.getByRole("button", {name: "Scorez hidden. Show all results"});

    act(() => control.focus());
    await user.keyboard("{Escape}");
    expect(screen.getByRole("region", {name: "Scorez start hidden"})).toBeInTheDocument();
    await user.tab();
    expect(screen.getByRole("button", {name: "Show all results"})).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", {name: "Got it"})).toHaveFocus();
    await user.keyboard("{Escape}");

    expect(control).toHaveFocus();
    expect(control).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    expect(localStorage.getItem(SPOILER_ONBOARDING_STORAGE_KEY)).toBe("true");
  });

  it("ordinary clicks keep onboarding open and do not reveal results", async () => {
    const user = userEvent.setup();
    render(header());
    await user.click(screen.getByRole("heading", {name: "Scorez start hidden"}));
    await user.click(document.body);
    expect(screen.getByRole("region", {name: "Scorez start hidden"})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Scorez hidden. Show all results"})).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", {name: "Scorez hidden. Show all results"})).toHaveTextContent("Scorez hidden");
  });

  it("closes an active hint when another tab enables global results", () => {
    render(header("playoffs"));
    act(() => window.dispatchEvent(new StorageEvent("storage", {
      key: RESULTS_VISIBILITY_STORAGE_KEY,
      newValue: "true",
    })));
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Results shown. Hide all results"})).toHaveAttribute("aria-pressed", "true");
  });
});

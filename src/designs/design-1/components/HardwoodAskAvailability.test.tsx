import {render, screen} from "@testing-library/react";
import {MemoryRouter} from "react-router";
import {afterEach, describe, expect, it, vi} from "vitest";
import {ThemeContext} from "@/context/ThemeContext";
import {ResultsVisibilityProvider} from "@/providers/ResultsVisibilityProvider";
import HardwoodHeader from "./HardwoodHeader";

function renderHeader() {
  return render(
    <MemoryRouter>
      <ThemeContext.Provider value={{theme: "light", toggleTheme: vi.fn()}}>
        <ResultsVisibilityProvider><HardwoodHeader section="scores" /></ResultsVisibilityProvider>
      </ThemeContext.Provider>
    </MemoryRouter>,
  );
}

describe("Design 1 Ask availability", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("hides Ask in production unless the frontend flag is enabled", () => {
    vi.stubEnv("DEV", false);
    vi.stubEnv("VITE_ASK_ENABLED", "");
    const view = renderHeader();
    expect(screen.queryByRole("button", {name: "Ask about a game, stat, or series"})).not.toBeInTheDocument();
    view.unmount();

    vi.stubEnv("VITE_ASK_ENABLED", "1");
    renderHeader();
    expect(screen.getByRole("button", {name: "Ask about a game, stat, or series"})).toBeInTheDocument();
  });

  it("keeps Ask available in development", () => {
    vi.stubEnv("DEV", true);
    vi.stubEnv("VITE_ASK_ENABLED", "");
    renderHeader();
    expect(screen.getByRole("button", {name: "Ask about a game, stat, or series"})).toBeInTheDocument();
  });
});

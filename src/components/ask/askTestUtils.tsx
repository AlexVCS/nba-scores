/* eslint-disable react-refresh/only-export-components -- test-only helpers */
// Test-only helpers for Ask component tests.
import type {ReactNode} from "react";
import {QueryClient, QueryClientProvider} from "@tanstack/react-query";
import {MemoryRouter, Route, Routes, useLocation} from "react-router";
import {vi} from "vitest";
import {ThemeContext} from "@/context/ThemeContext";
import {ResultsVisibilityProvider} from "@/providers/ResultsVisibilityProvider";

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.search}</output>;
}

export function AskTestProviders({children, path = "/?date=2026-02-05"}: {children: ReactNode; path?: string}) {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <ThemeContext.Provider value={{theme: "light", toggleTheme: vi.fn()}}>
          <ResultsVisibilityProvider>
            <Routes>
              <Route path="*" element={<>{children}<LocationProbe /></>} />
            </Routes>
          </ResultsVisibilityProvider>
        </ThemeContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

/** Everything a sighted or screen-reader user could perceive: text plus accessible-name attributes. */
export function perceivableText(root: HTMLElement): string {
  const attributes = Array.from(root.querySelectorAll("*")).flatMap(element =>
    ["aria-label", "title", "alt", "aria-description", "aria-valuetext"]
      .map(name => element.getAttribute(name))
      .filter((value): value is string => Boolean(value)));
  return `${root.textContent ?? ""}\n${attributes.join("\n")}`;
}

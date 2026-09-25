import {StrictMode, type ReactNode} from "react";
import {act, cleanup, render, renderHook} from "@testing-library/react";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {useResultsVisibility} from "@/hooks/useResultsVisibility";
import {
  RESULTS_VISIBILITY_STORAGE_KEY,
  SPOILER_ONBOARDING_STORAGE_KEY,
  ResultsVisibilityProvider,
} from "./ResultsVisibilityProvider";

const LEGACY_RESULTS_VISIBILITY_STORAGE_KEY = "nba-scorez:design-4:show-all-results";

function wrapper({children}: {children: ReactNode}) {
  return <StrictMode><ResultsVisibilityProvider>{children}</ResultsVisibilityProvider></StrictMode>;
}

function receiveStorage(key: string, newValue: string) {
  act(() => window.dispatchEvent(new StorageEvent("storage", {key, newValue})));
}

describe("ResultsVisibilityProvider spoiler onboarding", () => {
  beforeEach(() => window.localStorage.clear());

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it("starts fresh visitors with hidden results and an unacknowledged hint in Strict Mode", () => {
    const {result} = renderHook(useResultsVisibility, {wrapper});

    expect(result.current.showAllResults).toBe(false);
    expect(result.current.isSpoilerHintDismissed).toBe(false);
    expect(window.localStorage.getItem(RESULTS_VISIBILITY_STORAGE_KEY)).toBe("false");
    expect(window.localStorage.getItem(SPOILER_ONBOARDING_STORAGE_KEY)).toBeNull();
  });

  it("dismisses without revealing and remembers dismissal across provider remounts", () => {
    const first = renderHook(useResultsVisibility, {wrapper});
    act(() => first.result.current.dismissSpoilerHint());

    expect(first.result.current.showAllResults).toBe(false);
    expect(first.result.current.isSpoilerHintDismissed).toBe(true);
    expect(window.localStorage.getItem(SPOILER_ONBOARDING_STORAGE_KEY)).toBe("true");

    first.unmount();
    const second = renderHook(useResultsVisibility, {wrapper});
    expect(second.result.current.showAllResults).toBe(false);
    expect(second.result.current.isSpoilerHintDismissed).toBe(true);
  });

  it.each([RESULTS_VISIBILITY_STORAGE_KEY, LEGACY_RESULTS_VISIBILITY_STORAGE_KEY])(
    "acknowledges enabled results stored under %s on the first render",
    key => {
      window.localStorage.setItem(key, "true");
      const renderStates: boolean[] = [];
      const {result} = renderHook(() => {
        const context = useResultsVisibility();
        renderStates.push(context.isSpoilerHintDismissed);
        return context;
      }, {wrapper});

      expect(renderStates.every(Boolean)).toBe(true);
      expect(result.current.showAllResults).toBe(true);
      expect(window.localStorage.getItem(SPOILER_ONBOARDING_STORAGE_KEY)).toBe("true");

      act(() => result.current.setShowAllResults(false));
      expect(result.current.isSpoilerHintDismissed).toBe(true);
    },
  );

  it("reads saved dismissal before the first render", () => {
    window.localStorage.setItem(SPOILER_ONBOARDING_STORAGE_KEY, "true");
    const renderStates: boolean[] = [];
    renderHook(() => {
      const context = useResultsVisibility();
      renderStates.push(context.isSpoilerHintDismissed);
      return context;
    }, {wrapper});

    expect(renderStates.every(Boolean)).toBe(true);
  });

  it("prefers the current hidden preference over the legacy enabled preference", () => {
    window.localStorage.setItem(RESULTS_VISIBILITY_STORAGE_KEY, "false");
    window.localStorage.setItem(LEGACY_RESULTS_VISIBILITY_STORAGE_KEY, "true");
    const {result} = renderHook(useResultsVisibility, {wrapper});

    expect(result.current.showAllResults).toBe(false);
    expect(result.current.isSpoilerHintDismissed).toBe(false);
  });

  it("explicitly enables results without inverting an already enabled preference", () => {
    const {result} = renderHook(useResultsVisibility, {wrapper});
    act(() => result.current.setShowAllResults(true));
    act(() => result.current.setShowAllResults(true));

    expect(result.current.showAllResults).toBe(true);
    expect(result.current.isSpoilerHintDismissed).toBe(true);
    expect(window.localStorage.getItem(SPOILER_ONBOARDING_STORAGE_KEY)).toBe("true");

    act(() => result.current.setShowAllResults(false));
    expect(result.current.showAllResults).toBe(false);
    expect(result.current.isSpoilerHintDismissed).toBe(true);
  });

  it("retains acknowledgment when the global toggle is switched back off", () => {
    const {result} = renderHook(useResultsVisibility, {wrapper});
    act(() => result.current.toggleShowAllResults());
    expect(result.current.showAllResults).toBe(true);
    expect(result.current.isSpoilerHintDismissed).toBe(true);

    act(() => result.current.toggleShowAllResults());
    expect(result.current.showAllResults).toBe(false);
    expect(result.current.isSpoilerHintDismissed).toBe(true);
  });

  it("acknowledges dismissal from another tab without revealing results", () => {
    const {result} = renderHook(useResultsVisibility, {wrapper});
    receiveStorage(SPOILER_ONBOARDING_STORAGE_KEY, "true");

    expect(result.current.isSpoilerHintDismissed).toBe(true);
    expect(result.current.showAllResults).toBe(false);
  });

  it("acknowledges a global reveal from another tab and stays acknowledged when hidden again", () => {
    const {result} = renderHook(useResultsVisibility, {wrapper});
    receiveStorage(RESULTS_VISIBILITY_STORAGE_KEY, "true");

    expect(result.current.showAllResults).toBe(true);
    expect(result.current.isSpoilerHintDismissed).toBe(true);
    expect(window.localStorage.getItem(SPOILER_ONBOARDING_STORAGE_KEY)).toBe("true");

    receiveStorage(RESULTS_VISIBILITY_STORAGE_KEY, "false");
    expect(result.current.showAllResults).toBe(false);
    expect(result.current.isSpoilerHintDismissed).toBe(true);
  });

  it("ignores unrelated storage and sessionStorage events", () => {
    const {result} = renderHook(useResultsVisibility, {wrapper});
    receiveStorage("unrelated-preference", "true");
    act(() => window.dispatchEvent(new StorageEvent("storage", {
      key: RESULTS_VISIBILITY_STORAGE_KEY,
      newValue: "true",
      storageArea: window.sessionStorage,
    })));

    expect(result.current.showAllResults).toBe(false);
    expect(result.current.isSpoilerHintDismissed).toBe(false);
  });

  it.each(["dismiss", "reveal"])(
    "keeps %s in memory across consumer remounts when storage is unavailable",
    action => {
      vi.spyOn(console, "log").mockImplementation(() => undefined);
      vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
        throw new Error("Storage unavailable");
      });
      vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
        throw new Error("Storage unavailable");
      });
      let context: ReturnType<typeof useResultsVisibility> | undefined;
      function Consumer() {
        context = useResultsVisibility();
        return null;
      }
      const {rerender} = render(
        <ResultsVisibilityProvider><Consumer key="scores" /></ResultsVisibilityProvider>,
      );

      act(() => {
        if (action === "dismiss") context!.dismissSpoilerHint();
        else context!.setShowAllResults(true);
      });
      rerender(<ResultsVisibilityProvider><Consumer key="playoffs" /></ResultsVisibilityProvider>);

      expect(context!.isSpoilerHintDismissed).toBe(true);
      expect(context!.showAllResults).toBe(action === "reveal");
    },
  );

  it("handles denied localStorage access without crashing actions or storage events", () => {
    const storageArea = window.localStorage;
    vi.spyOn(console, "log").mockImplementation(() => undefined);
    vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new Error("Storage access denied");
    });
    const {result} = renderHook(useResultsVisibility, {wrapper});
    expect(result.current.showAllResults).toBe(false);

    act(() => result.current.dismissSpoilerHint());
    act(() => result.current.setShowAllResults(true));
    act(() => window.dispatchEvent(new StorageEvent("storage", {
      key: RESULTS_VISIBILITY_STORAGE_KEY,
      newValue: "false",
      storageArea,
    })));

    expect(result.current.showAllResults).toBe(true);
    expect(result.current.isSpoilerHintDismissed).toBe(true);
  });
});

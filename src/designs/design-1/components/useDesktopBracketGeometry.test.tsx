import {cleanup, render} from "@testing-library/react";
import {afterEach, describe, expect, it, vi} from "vitest";
import useDesktopBracketGeometry from "./useDesktopBracketGeometry";

function MeasurementBracket({season = "1952-53"}: {season?: string}) {
  const ref = useDesktopBracketGeometry(season);
  return (
    <div ref={ref} data-testid="bracket">
      <div className="hw-bracket-measure" aria-hidden="true">
        <div data-height="98" />
        <div data-height="126" />
        <div data-height="154" />
      </div>
      <div className="hw-bracket-measure" data-finals-measure aria-hidden="true">
        <div data-height="176" />
      </div>
    </div>
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("desktop bracket measurements", () => {
  it("reserves locked and historical card heights before reveal and remeasures wrapping", () => {
    let resize: () => void = () => {};
    const observe = vi.fn();
    const disconnect = vi.fn();
    vi.stubGlobal("ResizeObserver", class {
      constructor(callback: () => void) { resize = callback; }
      observe = observe;
      disconnect = disconnect;
    });
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      return {height: Number(this.dataset.height ?? 0)} as DOMRect;
    });
    const {getByTestId, unmount} = render(<MeasurementBracket />);
    const bracket = getByTestId("bracket");
    expect(bracket.style.getPropertyValue("--hw-bracket-card-height")).toBe("154px");
    expect(bracket.style.getPropertyValue("--hw-bracket-finals-height")).toBe("176px");
    expect(observe).toHaveBeenCalledTimes(4);

    const wrappedLock = bracket.querySelector<HTMLElement>('[data-height="154"]')!;
    wrappedLock.dataset.height = "214.25";
    resize();
    expect(bracket.style.getPropertyValue("--hw-bracket-card-height")).toBe("215px");
    wrappedLock.dataset.height = "114";
    resize();
    expect(bracket.style.getPropertyValue("--hw-bracket-card-height")).toBe("126px");
    unmount();
    expect(disconnect).toHaveBeenCalledOnce();
  });

  it("supports non-layout environments without ResizeObserver", () => {
    vi.stubGlobal("ResizeObserver", undefined);
    expect(() => render(<MeasurementBracket />)).not.toThrow();
  });
});

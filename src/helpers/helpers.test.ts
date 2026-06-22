import {describe, expect, it} from "vitest";
import {formatMinutesPlayed} from "./helpers";

describe("formatMinutesPlayed", () => {
  it("formats NBA clock minutes", () => {
    expect(formatMinutesPlayed("40:09")).toBe("40");
    expect(formatMinutesPlayed("8:31")).toBe("8");
  });

  it("formats duration minutes", () => {
    expect(formatMinutesPlayed("PT40M09S")).toBe("40");
  });

  it("preserves DNP empty minutes", () => {
    expect(formatMinutesPlayed("")).toBe("");
  });
});

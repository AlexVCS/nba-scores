import {beforeEach, describe, expect, it} from "vitest";
import {ASK_RECENT_LIMIT, ASK_RECENT_STORAGE_KEY, addRecentSearch, clearRecentSearches, readRecentSearches} from "./recentSearches";

describe("Ask recent searches", () => {
  beforeEach(() => localStorage.clear());

  it("keeps the newest questions first, deduped case-insensitively, up to the limit", () => {
    for (let index = 0; index < ASK_RECENT_LIMIT + 3; index++) addRecentSearch(`question ${index}`);
    addRecentSearch("QUESTION 8");

    const recents = readRecentSearches();
    expect(recents).toHaveLength(ASK_RECENT_LIMIT);
    expect(recents[0].question).toBe("QUESTION 8");
    expect(recents.filter(recent => recent.question.toLowerCase() === "question 8")).toHaveLength(1);
  });

  it("stores only the question text and time", () => {
    addRecentSearch("  Who won the 2024 NBA Finals?  ", new Date("2026-09-29T12:00:00Z"));
    expect(JSON.parse(localStorage.getItem(ASK_RECENT_STORAGE_KEY)!)).toEqual([
      {question: "Who won the 2024 NBA Finals?", askedAt: "2026-09-29T12:00:00.000Z"},
    ]);
  });

  it("ignores malformed storage and clears", () => {
    localStorage.setItem(ASK_RECENT_STORAGE_KEY, JSON.stringify([{question: 4}, "x", {question: "ok", askedAt: "t", answer: "leak"}]));
    expect(readRecentSearches()).toEqual([{question: "ok", askedAt: "t"}]);
    expect(clearRecentSearches()).toEqual([]);
    expect(readRecentSearches()).toEqual([]);
  });
});

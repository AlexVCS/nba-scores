import {afterEach, describe, expect, it, vi} from "vitest";
import {ASK_RESPONSE_FIXTURES} from "@/services/ask/fixtures";
import {AskServiceError, getAskSuggestions, postAsk} from "./askService";

afterEach(() => vi.unstubAllGlobals());

describe("askService", () => {
  it("posts the question, context, and resolution token", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(ASK_RESPONSE_FIXTURES["answer-player-stat"])));
    vi.stubGlobal("fetch", fetchMock);

    await postAsk({question: "  how did jalen do  ", context: {route: "scores"}, resolution: "rsv_1"});

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/ask$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({question: "how did jalen do", context: {route: "scores"}, resolution: "rsv_1"});
  });

  it("returns contract responses even on non-2xx statuses, such as budget exhaustion", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(ASK_RESPONSE_FIXTURES["budget-exhausted"]), {status: 429})));
    await expect(postAsk({question: "q"})).resolves.toMatchObject({outcome: "budget_exhausted"});
  });

  it("throws a transport error when no AskResponse comes back", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>", {status: 502})));
    await expect(postAsk({question: "q"})).rejects.toBeInstanceOf(AskServiceError);

    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("offline");
    }));
    await expect(postAsk({question: "q"})).rejects.toBeInstanceOf(AskServiceError);
  });

  it("requests typeahead suggestions with the hidden flag", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({query: "knicks", games: [], entities: [], questions: []})));
    vi.stubGlobal("fetch", fetchMock);
    await getAskSuggestions("knicks", true);
    const [url] = fetchMock.mock.calls[0] as unknown as [string];
    expect(url).toMatch(/\/ask\/suggest\?q=knicks&hidden=true$/);
  });
});

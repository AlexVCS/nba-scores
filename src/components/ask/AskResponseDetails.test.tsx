import {render, screen, within} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {afterEach, describe, expect, it, vi} from "vitest";
import {ASK_RESPONSE_FIXTURES} from "@/services/ask/fixtures";
import type {AskResponse} from "@/services/ask/types";
import AskFooter from "./AskFooter";

function renderFooter(response: AskResponse) {
  return render(<AskFooter mode="result" response={response} />);
}

describe("Ask response details", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("reveals the reported interpreter model and call status in development", async () => {
    vi.stubEnv("DEV", true);
    const response = structuredClone(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    response.interpreter = {...response.interpreter, model: "gpt-6-luna", adapter: "openai_responses"};
    renderFooter(response);

    const details = screen.getByText("Response details").closest("details");
    expect(details).not.toHaveAttribute("open");
    await userEvent.setup().click(screen.getByText("Response details"));
    expect(details).toHaveAttribute("open");
    expect(within(details as HTMLElement).getByText("gpt-6-luna")).toBeInTheDocument();
    expect(within(details as HTMLElement).getByText("openai_responses")).toBeInTheDocument();
    expect(within(details as HTMLElement).getByText("Model call this request").nextElementSibling).toHaveTextContent("Yes");
  });

  it("shows which cascade tier decided each field", async () => {
    vi.stubEnv("DEV", true);
    const response = structuredClone(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    response.interpreter = {
      ...response.interpreter, adapter: "cascade", model: "jev-1.13.0+gpt-6-luna",
      field_tiers: {intent: "jev", game_number: "luna", teams: "veto"},
    };
    renderFooter(response);
    await userEvent.setup().click(screen.getByText("Response details"));

    expect(screen.getByText("Decided by").nextElementSibling).toHaveTextContent(
      "intent: Jev · game number: Luna · teams: Tiers disagreed",
    );
  });

  it("distinguishes cached interpretation from a new model call", async () => {
    vi.stubEnv("DEV", true);
    const response = structuredClone(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    response.interpreter = {...response.interpreter, model_called: false, cache_hit: true, model: "gpt-6-luna", adapter: "openai_responses"};
    renderFooter(response);
    await userEvent.setup().click(screen.getByText("Response details"));

    expect(screen.getByText("Model call this request").nextElementSibling).toHaveTextContent("No");
    expect(screen.getByText("Cache hit").nextElementSibling).toHaveTextContent("Yes");
    expect(screen.getByText("gpt-6-luna")).toBeInTheDocument();
  });

  it("shows the original parser model on a clarification continuation", async () => {
    vi.stubEnv("DEV", true);
    const response = structuredClone(ASK_RESPONSE_FIXTURES["clarification-two-step-year"]);
    response.interpreter = {...response.interpreter, model_called: false, cache_hit: false, model: "gpt-6-luna", adapter: "openai_responses"};
    renderFooter(response);
    await userEvent.setup().click(screen.getByText("Response details"));

    expect(screen.getByText("Model call this request").nextElementSibling).toHaveTextContent("No");
    expect(screen.getByText("Cache hit").nextElementSibling).toHaveTextContent("No");
    expect(screen.getByText("gpt-6-luna")).toBeInTheDocument();
    expect(screen.queryByText("No model used for this response")).not.toBeInTheDocument();
  });

  it("says when a direct response used no model", async () => {
    vi.stubEnv("DEV", true);
    renderFooter(ASK_RESPONSE_FIXTURES["unsupported-career-stats"]);
    await userEvent.setup().click(screen.getByText("Response details"));

    expect(screen.getByText("No model used for this response")).toBeInTheDocument();
    expect(screen.queryByText("Interpreted by")).not.toBeInTheDocument();
  });

  it("omits response details outside development", () => {
    vi.stubEnv("DEV", false);
    renderFooter(ASK_RESPONSE_FIXTURES["answer-player-stat"]);
    expect(screen.queryByText("Response details")).not.toBeInTheDocument();
  });
});

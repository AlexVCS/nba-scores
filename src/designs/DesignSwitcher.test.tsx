import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter} from "react-router";
import {describe, expect, it} from "vitest";
import DesignSwitcher from "./DesignSwitcher";

const DESIGN_PREVIEW_BASE_PATH = "/preview/test-token-that-is-at-least-32-characters";
function renderSwitcher() {
  return render(
    <MemoryRouter initialEntries={[`${DESIGN_PREVIEW_BASE_PATH}/design-2/games/0042500131/boxscore?date=2026-04-18#stats`]}>
      <DesignSwitcher activeDesign="design-2" />
    </MemoryRouter>,
  );
}

describe("DesignSwitcher", () => {
  it("marks the active design and maps equivalent deep links", () => {
    renderSwitcher();
    expect(screen.getByRole("link", {name: "View Broadcast ’96 design"})).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", {name: "View Original Scorez design"})).toHaveAttribute(
      "href",
      `${DESIGN_PREVIEW_BASE_PATH}/original/games/0042500131/boxscore?date=2026-04-18#stats`,
    );
    expect(screen.getByRole("link", {name: "View Swiss Stat Lab design"})).toHaveAttribute(
      "href",
      `${DESIGN_PREVIEW_BASE_PATH}/design-5/games/0042500131/boxscore?date=2026-04-18#stats`,
    );
  });

  it("opens and dismisses the mobile design sheet", async () => {
    const user = userEvent.setup();
    renderSwitcher();
    await user.click(screen.getByRole("button", {name: /design 2/i}));
    expect(screen.getByRole("dialog", {name: "Choose application design"})).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", {name: "Choose application design"})).not.toBeInTheDocument();
  });
});

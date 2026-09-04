import {render, screen} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {MemoryRouter} from "react-router";
import {describe, expect, it} from "vitest";
import DesignSwitcher from "./DesignSwitcher";

function renderSwitcher() {
  return render(
    <MemoryRouter initialEntries={["/design-1/games/0042500131/boxscore?date=2026-04-18#stats"]}>
      <DesignSwitcher activeDesign="design-1" />
    </MemoryRouter>,
  );
}

describe("DesignSwitcher", () => {
  it("marks the active design and maps equivalent deep links", () => {
    renderSwitcher();
    expect(screen.getByRole("link", {name: "View Original Scorez design"})).toHaveTextContent("0");
    expect(screen.getByRole("link", {name: "View Gold on Hardwood design"})).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", {name: "View Original Scorez design"})).toHaveAttribute(
      "href",
      "/original/games/0042500131/boxscore?date=2026-04-18#stats",
    );
    expect(screen.getByRole("link", {name: "View Gold on Hardwood design"})).toHaveAttribute(
      "href",
      "/design-1/games/0042500131/boxscore?date=2026-04-18#stats",
    );
    expect(screen.getAllByRole("link", {name: /View .* design/})).toHaveLength(2);
  });

  it("opens and dismisses the mobile design sheet", async () => {
    const user = userEvent.setup();
    renderSwitcher();
    await user.click(screen.getByRole("button", {name: /design 1/i}));
    expect(screen.getByRole("dialog", {name: "Choose application design"})).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", {name: "Choose application design"})).not.toBeInTheDocument();
  });
});

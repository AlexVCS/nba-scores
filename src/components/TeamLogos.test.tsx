import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TeamLogos from "./TeamLogos";
import { ThemeContext } from "@/context/ThemeContext";

const renderWithTheme = (theme: "light" | "dark", ui: React.ReactElement) =>
  render(
    <ThemeContext.Provider value={{ theme, toggleTheme: () => {} }}>
      {ui}
    </ThemeContext.Provider>
  );

describe("TeamLogos", () => {
  it("uses the light CDN variant in light mode", () => {
    renderWithTheme("light", <TeamLogos teamName="Bulls" teamId={1610612741} size={40} />);
    const img = screen.getByRole("img", { name: "Bulls logo" });
    expect(img).toHaveAttribute("src", "https://cdn.nba.com/logos/nba/1610612741/global/L/logo.svg");
    expect(img).not.toHaveClass("team-logo--halo");
  });

  it("uses the dark CDN variant in dark mode", () => {
    renderWithTheme("dark", <TeamLogos teamName="Bulls" teamId={1610612741} size={40} />);
    const img = screen.getByRole("img", { name: "Bulls logo" });
    expect(img).toHaveAttribute("src", "https://cdn.nba.com/logos/nba/1610612741/global/D/logo.svg");
    expect(img).not.toHaveClass("team-logo--halo");
  });

  it("falls back to light mode without a ThemeProvider", () => {
    render(<TeamLogos teamName="Bulls" teamId={1610612741} size={40} />);
    expect(screen.getByRole("img", { name: "Bulls logo" })).toHaveAttribute(
      "src",
      "https://cdn.nba.com/logos/nba/1610612741/global/L/logo.svg"
    );
  });

  it("adds the halo class to historical logos", () => {
    renderWithTheme("dark", <TeamLogos teamName="Baltimore Bullets" teamId={123} size={40} tricode="bal" />);
    const img = screen.getByRole("img", { name: "Baltimore Bullets logo" });
    expect(img.getAttribute("src")).toContain("/images/historical-team-logos/bal-");
    expect(img).toHaveClass("team-logo--halo");
  });

  it("adds the halo class to the placeholder logo", () => {
    render(<TeamLogos teamId={0} size={40} />);
    expect(screen.getByRole("img", { name: "Placeholder team logo" })).toHaveClass("team-logo--halo");
  });
});

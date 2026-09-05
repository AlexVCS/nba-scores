import { fireEvent, render, screen } from "@testing-library/react";
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


describe("historical logo recovery", () => {
  it("distinguishes the Capitols from the Wizards despite their shared WAS code", () => {
    const { rerender } = render(<TeamLogos teamId={1610610036} tricode="WAS" size={64} />);
    expect(screen.getByRole("img").getAttribute("src")).toContain("was-washington-capitols");
    rerender(<TeamLogos teamId={1610612764} tricode="WAS" size={64} />);
    expect(screen.getByRole("img").getAttribute("src")).toContain("/1610612764/global/L/");
  });

  it.each(["AND", "CLR", "DEF", "INO", "MIH", "PIT", "SHE", "WAT", "DTF"])(
    "resolves recovered %s logos even without a team ID", (tricode) => {
      render(<TeamLogos teamId={0} tricode={tricode.toLowerCase()} size={64} />);
      expect(screen.getByRole("img").getAttribute("src")).toContain("/images/historical-team-logos/");
    }
  );

  it.each(["light", "dark"] as const)("tries both global themes, then both primary themes before the placeholder in %s mode", (theme) => {
    renderWithTheme(theme, <TeamLogos teamId={1610612741} size={40} />);
    const variant = theme === "dark" ? "D" : "L";
    const otherVariant = variant === "D" ? "L" : "D";
    expect(screen.getByRole("img").getAttribute("src")).toContain(`/global/${variant}/`);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByRole("img").getAttribute("src")).toContain(`/global/${otherVariant}/`);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByRole("img").getAttribute("src")).toContain(`/primary/${variant}/`);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByRole("img").getAttribute("src")).toContain(`/primary/${otherVariant}/`);
    fireEvent.error(screen.getByRole("img"));
    const placeholder = screen.getByRole("img", { name: "Placeholder team logo" });
    const source = placeholder.getAttribute("src");
    fireEvent.error(placeholder);
    expect(placeholder).toHaveAttribute("src", source);
  });

  it("resets a failed image when the team changes and avoids a modern historical substitute", () => {
    const { rerender } = render(<TeamLogos teamId={1610612737} tricode="MIH" size={64} />);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.getByRole("img", { name: "Placeholder team logo" })).toBeInTheDocument();
    rerender(<TeamLogos teamId={1610610036} tricode="WAS" size={64} />);
    expect(screen.getByRole("img").getAttribute("src")).toContain("was-washington-capitols");
  });
});

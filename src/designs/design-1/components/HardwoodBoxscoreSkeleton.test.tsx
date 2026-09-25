import {render, screen} from "@testing-library/react";
import {describe, expect, it} from "vitest";
import HardwoodBoxscoreSkeleton from "./HardwoodBoxscoreSkeleton";

describe("hardwood box score skeleton", () => {
  it("announces loading without matchup-style content", () => {
    render(<HardwoodBoxscoreSkeleton />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});

import "@testing-library/jest-dom/vitest";
import {vi} from "vitest";

vi.mock("@spectrum-icons/workflow/ChevronUpDown", () => ({
  default: () => null,
}));

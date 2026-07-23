import {describe, expect, it} from "vitest";
import {getDesignPreviewBasePath, isValidDesignPreviewToken} from "./previewConfig";

const TEST_TOKEN = "test-token-that-is-at-least-32-characters";
const TEST_TOKEN_HASH =
  "97a084bc3b97f8538b5479f3edb1f89f7cd904f8e1baa15f6d2ffba43bb59db7";

describe("design preview configuration", () => {
  it("extracts the unlisted preview base without treating public routes as previews", () => {
    expect(getDesignPreviewBasePath(`/preview/${TEST_TOKEN}/design-1/playoffs`))
      .toBe(`/preview/${TEST_TOKEN}`);
    expect(getDesignPreviewBasePath("/design-1")).toBeNull();
  });

  it("accepts only the token matching the expected fingerprint", async () => {
    await expect(isValidDesignPreviewToken(TEST_TOKEN, TEST_TOKEN_HASH)).resolves.toBe(true);
    await expect(isValidDesignPreviewToken(`${TEST_TOKEN}-wrong`, TEST_TOKEN_HASH)).resolves.toBe(false);
    await expect(isValidDesignPreviewToken("too-short", TEST_TOKEN_HASH)).resolves.toBe(false);
  });
});

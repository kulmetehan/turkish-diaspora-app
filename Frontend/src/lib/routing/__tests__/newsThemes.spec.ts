import { describe, expect, it, beforeEach, afterEach } from "vitest";

import {
  clearNewsThemesFromHash,
  readNewsThemesFromHash,
  writeNewsThemesToHash,
} from "@/lib/routing/newsThemes";

describe("newsThemes routing helpers", () => {
  beforeEach(() => {
    window.location.hash = "#/news";
  });

  afterEach(() => {
    window.location.hash = "#/";
  });

  it("parses comma separated and repeated values", () => {
    window.location.hash = "#/news?themes=politics,economy&themes=sports";
    expect(readNewsThemesFromHash()).toEqual(["politics", "economy", "sports"]);
  });

  it("writes normalized themes into the hash", () => {
    writeNewsThemesToHash(["Economy", "politics", "economy"]);
    const query = window.location.hash.split("?")[1] ?? "";
    const params = new URLSearchParams(query);
    expect(params.get("themes")).toBe("economy,politics");
    expect(readNewsThemesFromHash()).toEqual(["economy", "politics"]);
  });

  it("clears the themes parameter", () => {
    window.location.hash = "#/news?feed=diaspora&themes=security";
    clearNewsThemesFromHash();
    expect(window.location.hash).not.toContain("themes=");
  });
});


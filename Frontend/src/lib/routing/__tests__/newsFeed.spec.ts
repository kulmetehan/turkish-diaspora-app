import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  readNewsFeedFromHash,
  readNewsSearchQueryFromHash,
  writeNewsFeedToHash,
  writeNewsSearchQueryToHash,
  clearNewsSearchQueryFromHash,
} from "@/lib/routing/newsFeed";

describe("newsFeed routing helpers", () => {
  beforeEach(() => {
    window.location.hash = "#/news";
  });

  afterEach(() => {
    window.location.hash = "#/";
  });

  it("reads normalized feed and search query from the hash", () => {
    window.location.hash = "#/news?feed=tr&q=  rotterdam  ";
    expect(readNewsFeedFromHash()).toBe("tr");
    expect(readNewsSearchQueryFromHash()).toBe("rotterdam");
  });

  it("writes the search query while preserving other params", () => {
    window.location.hash = "#/news?feed=diaspora&themes=politics";
    writeNewsSearchQueryToHash("ankara");

    expect(window.location.hash).toContain("feed=diaspora");
    expect(window.location.hash).toContain("themes=politics");
    expect(window.location.hash).toContain("q=ankara");
  });

  it("removes the search parameter when writing an empty query", () => {
    window.location.hash = "#/news?q=hello";
    writeNewsSearchQueryToHash("  ");
    expect(window.location.hash).not.toContain("q=");
  });

  it("clears the search query explicitly", () => {
    window.location.hash = "#/news?feed=geo&q=festival";
    clearNewsSearchQueryFromHash();
    expect(window.location.hash).toContain("feed=geo");
    expect(window.location.hash).not.toContain("q=");
  });
});


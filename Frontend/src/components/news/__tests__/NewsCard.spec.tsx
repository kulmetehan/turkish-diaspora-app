import React, { act } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NewsItem } from "@/api/news";
import { NewsCard } from "@/components/news/NewsCard";

const BOOKMARK_ITEM: NewsItem = {
  id: 42,
  title: "Bookmark test",
  snippet: "Snippet",
  source: "Bron",
  published_at: "2025-11-22T08:00:00.000Z",
  url: "https://example.com/item",
  tags: [],
};

const SAMPLE_ITEM: NewsItem = {
  id: 1,
  title: "Turkse diaspora opent nieuw cultureel centrum",
  snippet: "Een nieuw ontmoetingspunt in Rotterdam wordt deze week feestelijk geopend.",
  source: "Rijnmond",
  published_at: "2025-11-22T09:15:00.000Z",
  url: "https://example.com/articles/1",
  image_url: "https://example.com/assets/1.jpg",
  tags: ["community", "rotterdam", "culture"],
};

// Ensure React treats this test file as act-enabled.
(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

function normalized(value: string) {
  return value.replace(/\s+/g, " ").trim();
}

describe("NewsCard bookmark toggle", () => {
  it("renders bookmark icon state", () => {
    render(<NewsCard item={BOOKMARK_ITEM} isBookmarked onToggleBookmark={() => undefined} />);
    const button = screen.getByLabelText(/Verwijder "Bookmark test" uit opgeslagen/i);
    expect(button.getAttribute("aria-pressed")).toBe("true");
  });

  it("toggles bookmark without opening the article", () => {
    const onToggle = vi.fn();
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    render(
      <NewsCard
        item={BOOKMARK_ITEM}
        isBookmarked={false}
        onToggleBookmark={onToggle}
      />,
    );
    const button = screen.getByLabelText(/Sla "Bookmark test" op/i);

    fireEvent.click(button);

    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(openSpy).not.toHaveBeenCalled();

    openSpy.mockRestore();
  });
});

describe("NewsCard", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    vi.restoreAllMocks();
  });

  it("renders title, snippet, source, formatted date, and tags", () => {
    act(() => {
      root.render(React.createElement(NewsCard, { item: SAMPLE_ITEM }));
    });

    const textContent = normalized(container.textContent ?? "");
    const expectedDate = new Intl.DateTimeFormat("nl-NL", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(SAMPLE_ITEM.published_at));

    expect(textContent).toContain(SAMPLE_ITEM.title);
    expect(textContent).toContain(SAMPLE_ITEM.snippet ?? "");
    expect(textContent).toContain(SAMPLE_ITEM.source);
    expect(textContent).toContain(normalized(expectedDate));

    const tagElements = Array.from(container.querySelectorAll("span")).filter((el) =>
      SAMPLE_ITEM.tags.includes(el.textContent ?? ""),
    );
    expect(tagElements.length).toBeGreaterThan(0);
  });

  it("opens the article URL when clicked", () => {
    const openSpy = vi.spyOn(window, "open").mockReturnValue(null);

    act(() => {
      root.render(React.createElement(NewsCard, { item: SAMPLE_ITEM }));
    });

    const card = container.querySelector('[role="button"]');
    expect(card).toBeTruthy();

    act(() => {
      card?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(openSpy).toHaveBeenCalledWith(SAMPLE_ITEM.url, "_blank", "noopener,noreferrer");
  });
});


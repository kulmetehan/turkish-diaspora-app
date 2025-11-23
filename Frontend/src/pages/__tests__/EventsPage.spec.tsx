import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

import type { UseEventsFeedResult } from "@/hooks/useEventsFeed";
import EventsPage from "@/pages/EventsPage";

const mockUseEventsFeed = vi.fn();

vi.mock("@/hooks/useEventsFeed", () => ({
  useEventsFeed: (...args: unknown[]) => mockUseEventsFeed(...args),
}));

const baseHookResult: UseEventsFeedResult = {
  items: [
    {
      id: 1,
      title: "Community Meetup",
      description: "Beschrijving",
      start_time_utc: "2025-01-01T18:00:00.000Z",
      end_time_utc: "2025-01-01T21:00:00.000Z",
      city_key: "rotterdam",
      category_key: "community",
      location_text: "Rotterdam Centrum",
      url: "https://example.com",
      source_key: "rotterdam_culture",
      summary_ai: null,
      updated_at: "2025-01-01T10:00:00.000Z",
      lat: 4.5,
      lng: 51.9,
    },
  ],
  isLoading: false,
  isLoadingMore: false,
  error: null,
  hasMore: false,
  reload: vi.fn(),
  loadMore: vi.fn(),
};

describe("EventsPage", () => {
  beforeEach(() => {
    mockUseEventsFeed.mockReturnValue(baseHookResult);
  });

  it("renders events list with data", () => {
    render(<EventsPage />);
    expect(() => screen.getByText("Events & bijeenkomsten")).not.toThrow();
    expect(() => screen.getByText("Community Meetup")).not.toThrow();
  });

  it("opens the detail overlay when Details is clicked", () => {
    render(<EventsPage />);
    const button = screen
      .getAllByRole("button", { name: /details/i })
      .find((element) => element.tagName === "BUTTON");
    expect(button).toBeDefined();
    fireEvent.click(button!);
    return waitFor(() => {
      expect(() => screen.getByRole("dialog")).not.toThrow();
    });
  });

  it("shows error state when the hook returns an error", () => {
    const errorResult: UseEventsFeedResult = {
      ...(baseHookResult as UseEventsFeedResult),
      items: [],
      error: "Kon events niet laden",
      isLoading: false,
      hasMore: false,
    };
    mockUseEventsFeed.mockReturnValueOnce(errorResult);
    render(<EventsPage />);
    expect(() => screen.getByText(/kon events niet laden/i)).not.toThrow();
  });
});



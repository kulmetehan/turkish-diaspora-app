import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi, type Mock } from "vitest";

import type { EventsListResponse } from "@/api/events";
import { fetchEvents } from "@/api/events";
import { useEventsFeed } from "@/hooks/useEventsFeed";

vi.mock("@/api/events", () => ({
  fetchEvents: vi.fn(),
}));

const mockFetchEvents = fetchEvents as unknown as Mock;

function createEventResponse(
  overrides: Partial<EventsListResponse> = {},
): EventsListResponse {
  return {
    items: [
      {
        id: 1,
        title: "Community Gathering",
        description: "Sample description",
        start_time_utc: "2025-01-01T18:00:00.000Z",
        end_time_utc: "2025-01-01T21:00:00.000Z",
        city_key: "rotterdam",
        category_key: "community",
        location_text: "Rotterdam Centrum",
        url: "https://example.com/event",
        source_key: "rotterdam_culture",
        summary_ai: null,
        updated_at: "2025-01-01T10:00:00.000Z",
      },
    ],
    total: 1,
    limit: 20,
    offset: 0,
    ...overrides,
  };
}

describe("useEventsFeed", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads events successfully", async () => {
    mockFetchEvents.mockResolvedValueOnce(createEventResponse());
    const { result } = renderHook(() => useEventsFeed());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.items).toHaveLength(1);
    expect(result.current.error).toBeNull();
  });

  it("captures errors from the API", async () => {
    mockFetchEvents.mockRejectedValueOnce(new Error("Network error"));
    const { result } = renderHook(() => useEventsFeed());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe("Network error");
    expect(result.current.items).toHaveLength(0);
  });

  it("appends additional pages when loadMore is called", async () => {
    mockFetchEvents
      .mockResolvedValueOnce(createEventResponse({ total: 2, limit: 1 }))
      .mockResolvedValueOnce(
        createEventResponse({
          items: [
            {
              id: 2,
              title: "Business Meetup",
              description: null,
              start_time_utc: "2025-01-05T09:00:00.000Z",
              end_time_utc: null,
              city_key: "amsterdam",
              category_key: "business",
              location_text: "Amsterdam",
              url: null,
              source_key: "amsterdam_business",
              summary_ai: null,
              updated_at: "2025-01-04T10:00:00.000Z",
            },
          ],
          total: 2,
          offset: 1,
        }),
      );

    const { result } = renderHook(() => useEventsFeed({ pageSize: 1 }));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.items).toHaveLength(1);

    result.current.loadMore();

    await waitFor(() => expect(result.current.items).toHaveLength(2));
    expect(mockFetchEvents).toHaveBeenCalledTimes(2);
  });
});



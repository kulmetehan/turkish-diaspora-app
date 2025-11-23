import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { EventItem } from "@/api/events";
import { EventList } from "@/components/events/EventList";

const baseEvent: EventItem = {
  id: 1,
  title: "Community Meetup",
  description: "Desc",
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
};

describe("EventList", () => {
  it("renders events and triggers callbacks", () => {
    const handleSelect = vi.fn();
    const handleDetail = vi.fn();
    const handleShowOnMap = vi.fn();

    render(
      <EventList
        events={[baseEvent]}
        selectedId={null}
        onSelect={handleSelect}
        onSelectDetail={handleDetail}
        onShowOnMap={handleShowOnMap}
        hasMore={false}
      />,
    );

    const card = screen.getByText("Community Meetup").closest("[role='button']");
    expect(card).not.toBeNull();
    fireEvent.click(card!);
    expect(handleSelect).toHaveBeenCalledWith(1);

    const detailsButton = screen
      .getAllByRole("button", { name: /details/i })
      .find((element) => element.tagName === "BUTTON");
    expect(detailsButton).toBeDefined();
    fireEvent.click(detailsButton!);
    expect(handleDetail).toHaveBeenCalledWith(1);

    const mapButton = screen
      .getAllByRole("button", { name: /toon op kaart/i })
      .find((element) => element.tagName === "BUTTON");
    expect(mapButton).toBeDefined();
    fireEvent.click(mapButton!);
    expect(handleShowOnMap).toHaveBeenCalled();
  });

  it("shows empty state when there are no events", () => {
    render(<EventList events={[]} selectedId={null} hasMore={false} />);
    expect(() => screen.getByText(/nog geen events beschikbaar/i)).not.toThrow();
  });
});



import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { EventItem } from "@/api/events";
import { EventDetailOverlay } from "@/components/events/EventDetailOverlay";

const baseEvent: EventItem = {
  id: 1,
  title: "Community Meetup",
  description: "Organiser description",
  start_time_utc: "2025-01-01T18:00:00.000Z",
  end_time_utc: "2025-01-01T20:00:00.000Z",
  city_key: "rotterdam",
  category_key: "community",
  location_text: "Offenbach, Germany",
  url: "https://example.com",
  source_key: "sahmeran_events",
  summary_ai: "AI summary goes here.",
  updated_at: "2025-01-01T09:00:00.000Z",
  lat: 52,
  lng: 4,
};

function renderOverlay(overrides: Partial<EventItem> = {}) {
  const event = { ...baseEvent, ...overrides };
  return render(<EventDetailOverlay event={event} open onClose={vi.fn()} />);
}

describe("EventDetailOverlay", () => {
  it("labels city_key as Regio", () => {
    renderOverlay();
    expect(screen.queryByText(/Regio:\s+Rotterdam/i)).toBeTruthy();
  });

  it("hides AI summary when description is long", () => {
    const utils = renderOverlay({ description: "x".repeat(200) });
    const dialog = utils.getByRole("dialog");
    expect(within(dialog).getAllByText("Beschrijving").length).toBeGreaterThan(0);
    expect(within(dialog).queryAllByText("AI-samenvatting").length).toBe(0);
  });

  it("shows AI summary when description missing", () => {
    const utils = renderOverlay({ description: "", summary_ai: "AI summary" });
    const dialog = utils.getByRole("dialog");
    expect(within(dialog).queryAllByText("AI-samenvatting").length).toBeGreaterThan(0);
    expect(within(dialog).queryByText("AI summary")).toBeTruthy();
  });
});



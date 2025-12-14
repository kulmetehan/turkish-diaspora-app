import type { EventItem } from "@/api/events";

function isValidDate(date: Date) {
  return Number.isFinite(date.getTime());
}

function humanizeKey(value?: string | null): string {
  if (!value) return "Onbekend";
  return value
    .split(/[_-]/g)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Formats event date range for display.
 * 
 * NOTE: Event times are currently hidden in the UI because the AI extraction
 * of event times from detail pages is not yet reliable enough. The backend
 * still extracts and stores start_time_utc and end_time_utc, but only dates
 * are shown to users. Once the extraction improves, this function can be
 * updated to show times again.
 * 
 * @param startIso - ISO string of start date/time
 * @param endIso - ISO string of end date/time (optional)
 * @returns Formatted date string (e.g., "Mon 15 Jan" or "Mon 15 Jan – Tue 16 Jan")
 */
export function formatEventDateRange(
  startIso?: string | null,
  endIso?: string | null,
): string {
  if (!startIso) return "Datum onbekend";
  const start = new Date(startIso);
  const end = endIso ? new Date(endIso) : null;
  if (!isValidDate(start)) return "Datum onbekend";

  const dateFormatter = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });

  const dateLabel = dateFormatter.format(start);

  // Temporarily hide event times - only show dates
  // The backend still extracts and stores times, but they're not reliable enough yet
  // to display to users. Once AI extraction from detail pages improves, we can
  // re-enable time display here.
  if (end && isValidDate(end)) {
    const sameDay =
      start.getUTCFullYear() === end.getUTCFullYear() &&
      start.getUTCMonth() === end.getUTCMonth() &&
      start.getUTCDate() === end.getUTCDate();

    if (sameDay) {
      return dateLabel;
    }
    const endDateLabel = dateFormatter.format(end);
    return `${dateLabel} – ${endDateLabel}`;
  }

  return dateLabel;
}

export function formatCityLabel(cityKey?: string | null): string {
  return humanizeKey(cityKey);
}

export function formatCategoryLabel(categoryKey?: string | null): string {
  return humanizeKey(categoryKey);
}

export function eventHasCoordinates(event: Pick<EventItem, "lat" | "lng">): boolean {
  // More robust check: handle null, undefined, and ensure they're finite numbers
  const lat = event.lat;
  const lng = event.lng;

  if (lat == null || lng == null) {
    if (process.env.NODE_ENV === 'development' && (lat != null || lng != null)) {
      console.debug(`[eventHasCoordinates] Missing coordinate: lat=${lat}, lng=${lng}`);
    }
    return false;
  }

  // Convert to number if it's a string (defensive)
  const latNum = typeof lat === 'string' ? parseFloat(lat) : lat;
  const lngNum = typeof lng === 'string' ? parseFloat(lng) : lng;

  const isValid = (
    typeof latNum === "number" &&
    Number.isFinite(latNum) &&
    typeof lngNum === "number" &&
    Number.isFinite(lngNum) &&
    !Number.isNaN(latNum) &&
    !Number.isNaN(lngNum)
  );

  if (process.env.NODE_ENV === 'development' && !isValid && (lat != null || lng != null)) {
    console.debug(`[eventHasCoordinates] Invalid coordinates: lat=${lat} (${typeof lat}) -> ${latNum} (${typeof latNum}), lng=${lng} (${typeof lng}) -> ${lngNum} (${typeof lngNum})`);
  }

  return isValid;
}





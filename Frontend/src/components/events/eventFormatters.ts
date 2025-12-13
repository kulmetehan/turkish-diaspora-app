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
  const timeFormatter = new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  const dateLabel = dateFormatter.format(start);

  // Format the time first to check if it's "00:00" in local time
  // This catches placeholder times that would show as "00:00" to the user
  const timeStart = timeFormatter.format(start);
  const startIsMidnight = timeStart === "00:00";

  if (end && isValidDate(end)) {
    const sameDay =
      start.getUTCFullYear() === end.getUTCFullYear() &&
      start.getUTCMonth() === end.getUTCMonth() &&
      start.getUTCDate() === end.getUTCDate();

    const timeEnd = timeFormatter.format(end);
    const endIsMidnight = timeEnd === "00:00";

    // If both times are midnight, only show date
    if (startIsMidnight && endIsMidnight) {
      return dateLabel;
    }

    // If only start is midnight, show date without start time
    if (startIsMidnight) {
      return `${dateLabel} – ${timeEnd}`;
    }

    // If only end is midnight, show date with start time
    if (endIsMidnight) {
      return `${dateLabel} · ${timeStart}`;
    }

    // Both times are valid
    if (sameDay) {
      return `${dateLabel} · ${timeStart} – ${timeEnd}`;
    }
    const endDateLabel = dateFormatter.format(end);
    return `${dateLabel} ${timeStart} – ${endDateLabel} ${timeEnd}`;
  }

  // No end time, check if start is midnight
  if (startIsMidnight) {
    return dateLabel;
  }

  return `${dateLabel} · ${timeStart}`;
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





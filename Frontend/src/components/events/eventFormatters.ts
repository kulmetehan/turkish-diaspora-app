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
  const timeStart = timeFormatter.format(start);
  if (end && isValidDate(end)) {
    const sameDay =
      start.getUTCFullYear() === end.getUTCFullYear() &&
      start.getUTCMonth() === end.getUTCMonth() &&
      start.getUTCDate() === end.getUTCDate();
    const timeEnd = timeFormatter.format(end);
    if (sameDay) {
      return `${dateLabel} · ${timeStart} – ${timeEnd}`;
    }
    const endDateLabel = dateFormatter.format(end);
    return `${dateLabel} ${timeStart} – ${endDateLabel} ${timeEnd}`;
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
  return (
    typeof event.lat === "number" &&
    Number.isFinite(event.lat) &&
    typeof event.lng === "number" &&
    Number.isFinite(event.lng)
  );
}



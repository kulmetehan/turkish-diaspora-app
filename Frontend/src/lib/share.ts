// Frontend/src/lib/share.ts
/**
 * Share utilities using Web Share API with clipboard fallback.
 */

export interface ShareData {
  title: string;
  text?: string;
  url?: string;
}

/**
 * Check if Web Share API is available.
 */
export function isWebShareAvailable(): boolean {
  return typeof navigator !== "undefined" && "share" in navigator;
}

/**
 * Share content using Web Share API or clipboard fallback.
 */
export async function share(data: ShareData): Promise<boolean> {
  const shareUrl = data.url || window.location.href;

  // Try Web Share API first (mobile browsers, modern desktop)
  if (isWebShareAvailable()) {
    try {
      await navigator.share({
        title: data.title,
        text: data.text || data.title,
        url: shareUrl,
      });
      return true;
    } catch (error: any) {
      // User cancelled or error occurred
      if (error.name === "AbortError") {
        return false; // User cancelled, don't show error
      }
      // Fall through to clipboard fallback
    }
  }

  // Fallback to clipboard
  try {
    const shareText = data.text
      ? `${data.title}\n\n${data.text}\n\n${shareUrl}`
      : `${data.title}\n\n${shareUrl}`;

    await navigator.clipboard.writeText(shareText);
    return true;
  } catch (error) {
    console.error("Failed to copy to clipboard:", error);
    return false;
  }
}

/**
 * Generate deep link URL for a location.
 */
export function getLocationUrl(locationId: number | string): string {
  const baseUrl = window.location.origin + window.location.pathname;
  return `${baseUrl}#/locations/${locationId}`;
}

/**
 * Generate deep link URL for a poll.
 */
export function getPollUrl(pollId: number | string): string {
  const baseUrl = window.location.origin + window.location.pathname;
  return `${baseUrl}#/polls/${pollId}`;
}

/**
 * Generate deep link URL for an event.
 */
export function getEventUrl(eventId: number | string): string {
  const baseUrl = window.location.origin + window.location.pathname;
  return `${baseUrl}#/events/${eventId}`;
}

/**
 * Share a location.
 */
export async function shareLocation(location: {
  id: number | string;
  name: string;
  category?: string | null;
}): Promise<boolean> {
  const url = getLocationUrl(location.id);
  const categoryText = location.category
    ? ` (${location.category})`
    : "";

  return share({
    title: `Check out ${location.name}${categoryText} on Turkspot!`,
    text: `I found this Turkish business on Turkspot: ${location.name}`,
    url,
  });
}

/**
 * Share a poll.
 */
export async function sharePoll(poll: {
  id: number | string;
  title: string;
  question?: string;
}): Promise<boolean> {
  const url = getPollUrl(poll.id);
  const text = poll.question
    ? poll.question
    : `Check out this poll: ${poll.title}`;

  return share({
    title: poll.title,
    text,
    url,
  });
}

/**
 * Share an event.
 */
export async function shareEvent(event: {
  id: number | string;
  title: string;
}): Promise<boolean> {
  const url = getEventUrl(event.id);
  return share({
    title: `Check out ${event.title} on Turkspot!`,
    text: `I found this event on Turkspot: ${event.title}`,
    url,
  });
}





















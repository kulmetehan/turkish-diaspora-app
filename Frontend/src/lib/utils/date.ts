// Frontend/src/lib/utils/date.ts
/**
 * Format a date as relative time (e.g., "2 minuten geleden", "gisteren", "vorige week").
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffWeeks = Math.floor(diffDays / 7);
  const diffMonths = Math.floor(diffDays / 30);
  const diffYears = Math.floor(diffDays / 365);

  if (diffSeconds < 60) {
    return "zojuist";
  } else if (diffMinutes < 60) {
    return `${diffMinutes} min${diffMinutes > 1 ? "uten" : "uut"} geleden`;
  } else if (diffHours < 24) {
    return `${diffHours} uur geleden`;
  } else if (diffDays === 1) {
    return "gisteren";
  } else if (diffDays < 7) {
    return `${diffDays} dagen geleden`;
  } else if (diffWeeks === 1) {
    return "vorige week";
  } else if (diffWeeks < 4) {
    return `${diffWeeks} weken geleden`;
  } else if (diffMonths === 1) {
    return "vorige maand";
  } else if (diffMonths < 12) {
    return `${diffMonths} maanden geleden`;
  } else if (diffYears === 1) {
    return "vorig jaar";
  } else {
    return `${diffYears} jaar geleden`;
  }
}






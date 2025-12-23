// Frontend/src/lib/mascotteMessages.ts
/**
 * Contextuele berichten systeem voor mascotte microfeedback.
 * Elke trigger type heeft meerdere berichten waaruit random wordt geselecteerd.
 */

export type MascotteTrigger =
  | "check_in"
  | "note_created"
  | "note_popular"
  | "week_active"
  | "role_changed"
  | "pause_detected";

/**
 * Bericht mapping per trigger type.
 * Alle berichten zijn in Turks en max 1 zin (zoals gespecificeerd).
 */
const MESSAGES: Record<MascotteTrigger, string[]> = {
  check_in: [
    "Buraları iyi biliyor gibisin.",
    "Mahalle seni görüyor.",
    "Buraya uğradığın için teşekkürler.",
    "Mahalle seni fark etti.",
  ],
  note_created: [
    "Bu söz tutuldu.",
    "Deneyimini paylaştın.",
    "Mahalle seni dinliyor.",
    "Sözün değerli.",
  ],
  note_popular: [
    "Bu söz tutuldu.",
    "Sözün dinleniyor.",
    "Mahalle seni duydu.",
    "Sözün yankılanıyor.",
  ],
  week_active: [
    "Bu hafta görünürdün.",
    "Mahalle seni gördü.",
    "Bu hafta aktiftin.",
    "Mahalle seni fark etti.",
  ],
  role_changed: [
    "Yeni bir rol kazandın.",
    "Mahalle seni fark etti.",
    "Rolün değişti.",
    "Mahalle seni tanıyor.",
  ],
  pause_detected: [
    "Ara vermek de olur.",
    "Yine bekleriz.",
    "Ara vermek normal.",
    "Döndüğünde bekleriz.",
  ],
};

/**
 * Get a random message for the given trigger type.
 * Optionally accepts context for future context-aware selection.
 *
 * @param trigger - The trigger type
 * @param context - Optional context data (for future use)
 * @returns A random message string
 */
export function getMascotteMessage(
  trigger: MascotteTrigger,
  context?: Record<string, any>
): string {
  const messages = MESSAGES[trigger];
  if (!messages || messages.length === 0) {
    // Fallback message if trigger not found
    return "Mahalle seni görüyor.";
  }

  // Random selection from available messages
  const randomIndex = Math.floor(Math.random() * messages.length);
  return messages[randomIndex];
}



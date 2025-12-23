// Frontend/src/hooks/useMascotteFeedback.tsx
import { MascotteFeedback } from "@/components/mascotte/MascotteFeedback";
import { getMascotteMessage, type MascotteTrigger } from "@/lib/mascotteMessages";
import { toast } from "sonner";
import { useRef, useCallback, useEffect } from "react";

/**
 * Rate limiting configuration
 */
const MIN_INTERVAL_MS = 30 * 1000; // 30 seconds between messages
const MAX_MESSAGES_PER_SESSION = 5; // Max 5 messages per session

/**
 * Session tracking for rate limiting
 */
let sessionMessageCount = 0;
const lastMessageTimes = new Map<MascotteTrigger, number>();

/**
 * Check if we can show a mascotte feedback message based on rate limiting.
 *
 * @param trigger - The trigger type
 * @returns true if message can be shown, false otherwise
 */
function canShowMessage(trigger: MascotteTrigger): boolean {
  // Check session limit
  if (sessionMessageCount >= MAX_MESSAGES_PER_SESSION) {
    return false;
  }

  // Check per-trigger interval
  const lastTime = lastMessageTimes.get(trigger);
  if (lastTime) {
    const timeSinceLastMessage = Date.now() - lastTime;
    if (timeSinceLastMessage < MIN_INTERVAL_MS) {
      return false;
    }
  }

  return true;
}

/**
 * Record that a message was shown (for rate limiting).
 *
 * @param trigger - The trigger type
 */
function recordMessageShown(trigger: MascotteTrigger): void {
  sessionMessageCount++;
  lastMessageTimes.set(trigger, Date.now());

  // Store in localStorage for persistence across page reloads
  try {
    const key = `mascotte_feedback_${trigger}`;
    localStorage.setItem(key, Date.now().toString());
  } catch (e) {
    // Ignore localStorage errors (e.g., in private browsing)
  }
}

/**
 * Hook for showing mascotte feedback messages with rate limiting.
 *
 * @returns Object with showMascotteFeedback function
 */
export function useMascotteFeedback() {
  const mountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  /**
   * Show a mascotte feedback message for the given trigger.
   * Respects rate limiting to prevent spam.
   *
   * @param trigger - The trigger type
   * @param context - Optional context data (for future use)
   */
  const showMascotteFeedback = useCallback((
    trigger: MascotteTrigger,
    context?: Record<string, any>
  ): void => {
    // Check if component is still mounted
    if (!mountedRef.current) {
      return;
    }

    // Check rate limiting
    if (!canShowMessage(trigger)) {
      // Graceful degradation: silently skip if rate limited
      return;
    }

    // Get message
    const message = getMascotteMessage(trigger, context);

    // Show toast with custom mascotte component
    toast.custom(
      (t) => (
        <MascotteFeedback message={message} className={t.visible ? "animate-in slide-in-from-top-2" : "animate-out slide-out-to-top-2"} />
      ),
      {
        duration: 4000, // 4 seconds auto-dismiss
        position: "top-center",
      }
    );

    // Record that message was shown
    recordMessageShown(trigger);
  }, []); // Empty dependency array - function doesn't depend on any props or state

  return {
    showMascotteFeedback,
  };
}


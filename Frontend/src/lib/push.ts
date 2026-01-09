// Frontend/src/lib/push.ts
// Push notification utilities for Web Push API

export interface PushSubscription {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
}

/**
 * Register service worker for push notifications.
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator)) {
    console.warn("Service workers not supported");
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
    });
    
    console.log("Service worker registered:", registration.scope);
    return registration;
  } catch (error) {
    console.error("Service worker registration failed:", error);
    return null;
  }
}

/**
 * Request push notification permission.
 */
export async function requestPushPermission(): Promise<NotificationPermission> {
  if (!("Notification" in window)) {
    console.warn("Notifications not supported");
    return "denied";
  }

  const permission = await Notification.requestPermission();
  return permission;
}

/**
 * Subscribe to push notifications.
 */
export async function subscribeToPush(
  registration: ServiceWorkerRegistration,
  vapidPublicKey?: string
): Promise<PushSubscription | null> {
  try {
    if (!vapidPublicKey) {
      console.error("VAPID public key is required for push subscription");
      throw new Error("VAPID public key is required for push subscription");
    }

    console.log("Converting VAPID key to Uint8Array...");
    console.log("Key length:", vapidPublicKey.length);
    console.log("Key (first 50 chars):", vapidPublicKey.substring(0, 50));
    
    const applicationServerKey = urlBase64ToUint8Array(vapidPublicKey);
    console.log("Converted key length:", applicationServerKey.length);
    console.log("First byte:", `0x${applicationServerKey[0].toString(16)}`);

    console.log("Subscribing to push notifications...");
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: applicationServerKey,
    });

    console.log("Push subscription successful!");
    console.log("Endpoint:", subscription.endpoint);

    return {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: arrayBufferToBase64(subscription.getKey("p256dh")!),
        auth: arrayBufferToBase64(subscription.getKey("auth")!),
      },
    };
  } catch (error) {
    console.error("Push subscription failed:", error);
    if (error instanceof Error) {
      console.error("Error name:", error.name);
      console.error("Error message:", error.message);
      console.error("Error stack:", error.stack);
      // Re-throw the error so it can be caught and displayed to the user
      throw error;
    }
    throw new Error(`Push subscription failed: ${String(error)}`);
  }
}

/**
 * Get existing push subscription.
 */
export async function getPushSubscription(
  registration: ServiceWorkerRegistration
): Promise<PushSubscription | null> {
  try {
    const subscription = await registration.pushManager.getSubscription();
    
    if (!subscription) {
      return null;
    }

    return {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: arrayBufferToBase64(subscription.getKey("p256dh")!),
        auth: arrayBufferToBase64(subscription.getKey("auth")!),
      },
    };
  } catch (error) {
    console.error("Failed to get push subscription:", error);
    return null;
  }
}

/**
 * Unsubscribe from push notifications.
 */
export async function unsubscribeFromPush(
  registration: ServiceWorkerRegistration
): Promise<boolean> {
  try {
    const subscription = await registration.pushManager.getSubscription();
    if (subscription) {
      await subscription.unsubscribe();
      return true;
    }
    return false;
  } catch (error) {
    console.error("Failed to unsubscribe from push:", error);
    return false;
  }
}

/**
 * Convert VAPID public key from URL-safe base64 to Uint8Array.
 * The Web Push API expects the public key as a Uint8Array of 65 bytes:
 * - 0x04 prefix (uncompressed point indicator)
 * - 32 bytes X coordinate
 * - 32 bytes Y coordinate
 * 
 * Note: Some key generators (like generate_vapid_keys.py) remove the 0x04 prefix,
 * so we need to add it back if it's missing.
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  // Remove any whitespace
  const cleanKey = base64String.trim();
  
  // Add padding if needed (base64 URL-safe format)
  const padding = "=".repeat((4 - (cleanKey.length % 4)) % 4);
  const base64 = (cleanKey + padding)
    .replace(/-/g, "+")
    .replace(/_/g, "/");
  
  try {
    // Decode base64 to binary string
    const rawData = window.atob(base64);
    const decodedArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
      decodedArray[i] = rawData.charCodeAt(i);
    }
    
    // Check if we have 64 bytes (without 0x04 prefix) or 65 bytes (with prefix)
    if (decodedArray.length === 64) {
      // Key is missing the 0x04 prefix, add it
      console.log("VAPID key missing 0x04 prefix, adding it...");
      const outputArray = new Uint8Array(65);
      outputArray[0] = 0x04; // Uncompressed point indicator
      outputArray.set(decodedArray, 1);
      return outputArray;
    } else if (decodedArray.length === 65) {
      // Key already has the prefix, validate it
      if (decodedArray[0] !== 0x04) {
        console.warn(`VAPID key has unexpected first byte: 0x${decodedArray[0].toString(16)}, expected 0x04`);
        // Still return it, let the browser decide
      }
      return decodedArray;
    } else {
      console.error(`Invalid VAPID key length: expected 64 or 65 bytes, got ${decodedArray.length}`);
      console.error(`Key (first 50 chars): ${cleanKey.substring(0, 50)}...`);
      throw new Error(`Invalid VAPID public key length: expected 64 or 65 bytes, got ${decodedArray.length}`);
    }
  } catch (error) {
    console.error("Error converting VAPID key:", error);
    console.error("Key value:", cleanKey.substring(0, 50) + "...");
    throw new Error(`Failed to convert VAPID public key: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * Convert ArrayBuffer to base64 string.
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

/**
 * Initialize push notifications (register service worker and request permission).
 * Note: Service worker is now registered automatically via pwa.ts, so this function
 * primarily handles push subscription.
 */
export async function initializePushNotifications(
  vapidPublicKey?: string
): Promise<{
  registration: ServiceWorkerRegistration | null;
  subscription: PushSubscription | null;
}> {
  // Get existing service worker registration (should already be registered by pwa.ts)
  if (!("serviceWorker" in navigator)) {
    console.warn("Service workers not supported");
    throw new Error("Service workers not supported in this browser");
  }

  let registration: ServiceWorkerRegistration | null = null;
  
  try {
    // Try to get existing registration
    registration = await navigator.serviceWorker.ready;
  } catch (error) {
    // If no registration exists, register now (fallback)
    console.warn("No service worker registration found, registering now...");
    registration = await registerServiceWorker();
    if (!registration) {
      throw new Error("Service worker could not be registered");
    }
  }

  // Request permission
  const permission = await requestPushPermission();
  if (permission !== "granted") {
    throw new Error(`Push notification permission denied (status: ${permission})`);
  }

  // Check for existing subscription
  let subscription = await getPushSubscription(registration);
  
  // If no existing subscription, create new one
  if (!subscription) {
    subscription = await subscribeToPush(registration, vapidPublicKey);
  }

  return { registration, subscription };
}






















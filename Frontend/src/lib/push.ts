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
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: vapidPublicKey 
        ? urlBase64ToUint8Array(vapidPublicKey)
        : undefined,
    });

    return {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: arrayBufferToBase64(subscription.getKey("p256dh")!),
        auth: arrayBufferToBase64(subscription.getKey("auth")!),
      },
    };
  } catch (error) {
    console.error("Push subscription failed:", error);
    return null;
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
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  
  return outputArray;
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
 */
export async function initializePushNotifications(
  vapidPublicKey?: string
): Promise<{
  registration: ServiceWorkerRegistration | null;
  subscription: PushSubscription | null;
}> {
  // Register service worker
  const registration = await registerServiceWorker();
  if (!registration) {
    return { registration: null, subscription: null };
  }

  // Request permission
  const permission = await requestPushPermission();
  if (permission !== "granted") {
    console.warn("Push notification permission denied");
    return { registration, subscription: null };
  }

  // Check for existing subscription
  let subscription = await getPushSubscription(registration);
  
  // If no existing subscription, create new one
  if (!subscription) {
    subscription = await subscribeToPush(registration, vapidPublicKey);
  }

  return { registration, subscription };
}


















// Frontend/public/sw.js
// Service Worker for PWA and Push Notifications
// Version: 2.0.0 (force update for notification debugging)

const APP_SHELL_CACHE = 'tda-app-shell-v2';
const STATIC_CACHE = 'tda-static-v2';
const API_CACHE = 'tda-api-cache-v2';

// App shell files - core HTML, CSS, JS that make the app work
const appShellFiles = [
  '/',
  '/index.html',
  '/manifest.json',
];

// Static assets that can be cached aggressively
const staticAssets = [
  // Icons
  '/icon-72x72.jpg',
  '/icon-96x96.jpg',
  '/icon-128x128.jpg',
  '/icon-144x144.jpg',
  '/icon-152x152.jpg',
  '/icon-192x192.jpg',
  '/icon-384x384.jpg',
  '/icon-512x512.jpg',
  '/apple-touch-icon.jpg',
  '/favicon.png',
];

// Install event - cache app shell and static assets
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');
  
  event.waitUntil(
    Promise.all([
      // Cache app shell
      caches.open(APP_SHELL_CACHE).then((cache) => {
        console.log('[Service Worker] Caching app shell');
        return cache.addAll(appShellFiles);
      }),
      // Cache static assets
      caches.open(STATIC_CACHE).then((cache) => {
        console.log('[Service Worker] Caching static assets');
        return cache.addAll(staticAssets);
      }),
    ]).catch((error) => {
      console.error('[Service Worker] Cache installation failed:', error);
    })
  );
  
  // Force activation of new service worker
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Delete old caches that don't match current versions
          if (
            cacheName !== APP_SHELL_CACHE &&
            cacheName !== STATIC_CACHE &&
            cacheName !== API_CACHE &&
            !cacheName.startsWith('tda-v')
          ) {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      // Take control of all pages immediately
      return self.clients.claim();
    })
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    event.respondWith(fetch(event.request));
    return;
  }
  
  // API requests - Network first, then cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache successful API responses (optional, can be removed if not needed)
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(API_CACHE).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // Network failed, try cache
          return caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // No cache, return offline response
            return new Response(
              JSON.stringify({ error: 'Offline', message: 'Geen internetverbinding' }),
              {
                status: 503,
                headers: { 'Content-Type': 'application/json' },
              }
            );
          });
        })
    );
    return;
  }
  
  // HTML requests - Network first, then offline fallback
  if (event.request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache HTML responses
          const responseClone = response.clone();
          caches.open(APP_SHELL_CACHE).then((cache) => {
            cache.put(event.request, responseClone);
          });
          return response;
        })
        .catch(() => {
          // Network failed, try cache
          return caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // No cache, return offline page
            return caches.match('/offline.html');
          });
        })
    );
    return;
  }
  
  // Static assets (images, fonts, CSS, JS) - Cache first, then network
  if (
    url.pathname.match(/\.(png|jpg|jpeg|gif|svg|webp|ico|woff|woff2|ttf|eot|css|js)$/i) ||
    staticAssets.includes(url.pathname)
  ) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        
        // Not in cache, fetch from network
        return fetch(event.request).then((response) => {
          // Cache successful responses
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(STATIC_CACHE).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        });
      })
    );
    return;
  }
  
  // Default: Network first, cache fallback
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        return response;
      })
      .catch(() => {
        return caches.match(event.request);
      })
  );
});

// Track recent notifications to prevent duplicates
const recentNotifications = new Map();
const NOTIFICATION_DEDUP_WINDOW = 5000; // 5 seconds

// Push event - handle incoming push notifications
self.addEventListener('push', (event) => {
  console.log('[Service Worker] Push notification received');
  
  // Clean up old entries from recentNotifications
  const now = Date.now();
  for (const [key, timestamp] of recentNotifications.entries()) {
    if (now - timestamp > NOTIFICATION_DEDUP_WINDOW) {
      recentNotifications.delete(key);
    }
  }
  
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data = { body: event.data.text() || 'You have a new notification' };
    }
  }
  
  const title = data.title || 'Turkish Diaspora App';
  // Create unique tag to prevent duplicate notifications
  // Use notification type + ID if available, otherwise use timestamp
  const notificationKey = data.tag || data.data?.id 
    ? `${data.tag || data.data?.type || 'notification'}-${data.data?.id || Date.now()}`
    : `${data.title || 'notification'}-${data.body || ''}-${Date.now()}`;
  
  // Check if we've shown this notification recently (deduplication)
  if (recentNotifications.has(notificationKey)) {
    const lastShown = recentNotifications.get(notificationKey);
    if (now - lastShown < NOTIFICATION_DEDUP_WINDOW) {
      console.log('[Service Worker] Duplicate notification suppressed:', notificationKey);
      return; // Skip showing duplicate notification
    }
  }
  
  // Mark this notification as shown
  recentNotifications.set(notificationKey, now);
  
  const uniqueTag = notificationKey;
  const options = {
    body: data.body || 'You have a new notification',
    icon: '/icon-192x192.jpg',
    badge: '/icon-72x72.jpg',
    data: data.data || {},
    tag: uniqueTag,
    requireInteraction: false,
    vibrate: [200, 100, 200],
    timestamp: Date.now(),
  };

  const minimalOptions = {
    body: options.body,
    data: options.data,
    tag: options.tag,
  };

  event.waitUntil(
    // Check service worker state and client visibility first
    self.clients.matchAll({ includeUncontrolled: true })
      .then(clients => {
        return Promise.all(clients.map(async (client) => {
          const focused = 'focused' in client ? client.focused : null;
          const visibilityState = 'visibilityState' in client ? client.visibilityState : null;
          return { focused, visibilityState, url: client.url };
        }));
      })
      .then(clientCheck => {
        const hasVisibleTab = clientCheck.some(c => c.visibilityState === 'visible');
        const hasFocusedTab = clientCheck.some(c => c.focused === true);
        
        // If there's a visible tab, Chrome may suppress notifications
        // Try with requireInteraction: true to force display
        const notificationOptions = hasVisibleTab || hasFocusedTab 
          ? { ...options, requireInteraction: true }
          : options;
        
        // Try with adjusted options first
        return self.registration.showNotification(title, notificationOptions)
          .then(() => {
            console.log('[Service Worker] showNotification promise resolved');
          })
          .catch((error) => {
            console.error('[Service Worker] Failed to show notification:', error);
            // Try minimal options as fallback (no icon/badge)
            return self.registration.showNotification(title, minimalOptions)
              .then(() => {
                console.log('[Service Worker] showNotification promise resolved (minimal options fallback)');
              })
              .catch((fallbackError) => {
                console.error('[Service Worker] Failed to show notification (minimal options):', fallbackError);
              });
          });
      })
      .catch((error) => {
        console.error('[Service Worker] Client check failed:', error);
        // Fallback: try notification anyway
        return self.registration.showNotification(title, options).catch(err => {
          console.error('[Service Worker] Fallback notification failed:', err);
        });
      })
  );
});

// Notification click event - handle user clicking on notification
self.addEventListener('notificationclick', (event) => {
  console.log('[Service Worker] Notification clicked');
  
  event.notification.close();

  const data = event.notification.data || {};
  let url = '/';
  const action = event.action;

  // Handle action buttons
  if (action === 'mark_read' && data.type === 'chat_message' && data.topic_id) {
    // Mark as read - just close notification, don't navigate
    // The app will handle marking as read when user visits the topic
    return;
  }

  // Check for explicit URL in data first (highest priority)
  // This allows system notifications and any notification type to specify a custom URL
  if (data.url) {
    url = data.url;
  }
  // Determine URL based on notification type (fallback for backward compatibility)
  else if (data.type === 'poll' && data.poll_id) {
    url = `/polls/${data.poll_id}`;
  } else if (data.type === 'trending' && data.location_id) {
    url = `/locations/${data.location_id}`;
  } else if (data.type === 'activity' && data.location_id) {
    url = `/locations/${data.location_id}`;
  } else if (data.type === 'chat_message' && data.topic_id) {
    url = `/chat/topic/${data.topic_id}`;
    // Add message_id to URL hash for deep linking to specific message
    if (data.message_id) {
      url += `#message-${data.message_id}`;
    }
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Try to find existing window with matching URL pattern
        const hashUrl = `#${url}`;
        for (const client of clientList) {
          const clientUrl = new URL(client.url);
          if (clientUrl.hash === hashUrl || clientUrl.pathname + clientUrl.hash === url) {
            if ('focus' in client) {
              return client.focus().then(() => {
                if ('navigate' in client && typeof client.navigate === 'function') {
                  return client.navigate(url);
                }
              });
            }
            return client.focus();
          }
        }
        // If no matching window found, check if any window is open
        if (clientList.length > 0) {
          // Focus existing window and navigate
          const client = clientList[0];
          if ('focus' in client) {
            return client.focus().then(() => {
              if ('navigate' in client && typeof client.navigate === 'function') {
                return client.navigate(url);
              } else {
                // Fallback: use postMessage to notify client to navigate
                client.postMessage({ type: 'navigate', url });
              }
            });
          }
        }
        // Otherwise, open a new window
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});

// Message event - handle messages from main thread
self.addEventListener('message', (event) => {
  console.log('[Service Worker] Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'navigate') {
    // Handle navigation requests from main thread
    clients.matchAll().then((clientList) => {
      clientList.forEach((client) => {
        if ('navigate' in client && typeof client.navigate === 'function') {
          client.navigate(event.data.url);
        }
      });
    });
  }
});

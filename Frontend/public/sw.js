// Frontend/public/sw.js
// Service Worker for Push Notifications

const CACHE_NAME = 'tda-v2';
const urlsToCache = [
  '/',
  '/index.html',
];

// Install event - cache resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Fetch event - DO NOT cache API requests, only serve static assets from cache
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Exclude API requests from caching - they're dynamic and user-specific
  if (url.pathname.startsWith('/api/')) {
    // Always fetch from network for API requests
    event.respondWith(fetch(event.request));
    return;
  }
  
  // For static assets, try cache first, then network
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        return response || fetch(event.request);
      })
  );
});

// Push event - handle incoming push notifications
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Turkish Diaspora App';
  const options = {
    body: data.body || 'You have a new notification',
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    data: data.data || {},
    tag: data.tag || 'default',
    requireInteraction: false,
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Notification click event - handle user clicking on notification
self.addEventListener('notificationclick', (event) => {
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

  // Determine URL based on notification type
  if (data.type === 'poll' && data.poll_id) {
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
              return client.focus().then(() => client.navigate(url));
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
              if ('navigate' in client) {
                return (client as any).navigate(url);
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


























// SecureChat service worker.
// Scope: "/" (served from the root by the /sw.js route in app.py, not from
// /static/, so it can control the whole app -- see app.py).

const CACHE_VERSION = 'v1';
const CACHE_NAME = `securechat-${CACHE_VERSION}`;

// Only unauthenticated, unchanging assets are safe to pre-cache at install time.
const PRECACHE_URLS = [
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Only handle simple same-origin GET requests. Everything else --
  // POST logins/forms, and importantly the /wss WebSocket upgrade --
  // is left completely untouched and goes straight to the network.
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) {
    return;
  }

  // Static assets (icons, manifest): cache-first, they don't change per-user.
  if (req.url.includes('/static/')) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          return res;
        });
      })
    );
    return;
  }

  // Pages (friends list, chat, login...): network-first, since they're
  // personalized and change constantly. Falls back to a cached copy only
  // when there's no network at all, so the app doesn't go blank offline.
  event.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
        return res;
      })
      .catch(() => caches.match(req))
  );
});

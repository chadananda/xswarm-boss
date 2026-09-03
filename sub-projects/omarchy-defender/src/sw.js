/**
 * Omarchy Defender - Service Worker
 * Provides offline support and asset caching
 */

const CACHE_NAME = 'omarchy-defender-v2';
const STATIC_CACHE = 'omarchy-static-v2';
const AUDIO_CACHE = 'omarchy-audio-v2';

// Static assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/splash.css',
  '/game.css',
  '/splash.js',
  '/game.js',
  '/manifest.json',
  'https://cdn.jsdelivr.net/npm/phaser@3.90.0/dist/phaser.min.js'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              return name !== STATIC_CACHE &&
                     name !== AUDIO_CACHE &&
                     name !== CACHE_NAME;
            })
            .map((name) => {
              console.log('[SW] Removing old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Handle audio files with stale-while-revalidate strategy
  // Serve cached version immediately, but always fetch fresh in background
  if (url.pathname.includes('/assets/audio/')) {
    // Strip query strings for cache key (e.g., ?v=2)
    const cacheKey = new Request(url.origin + url.pathname);

    event.respondWith(
      caches.open(AUDIO_CACHE)
        .then((cache) => {
          return cache.match(cacheKey)
            .then((cached) => {
              // Always fetch from network to check for updates
              const fetchPromise = fetch(event.request)
                .then((response) => {
                  if (response.ok) {
                    // Update cache with fresh version
                    cache.put(cacheKey, response.clone());
                  }
                  return response;
                })
                .catch(() => {
                  // Network failed, return cached version if available
                  return cached;
                });

              // Return cached version immediately if available
              // Otherwise wait for network
              return cached || fetchPromise;
            });
        })
    );
    return;
  }

  // Handle image assets
  if (url.pathname.includes('/assets/images/')) {
    event.respondWith(
      caches.open(CACHE_NAME)
        .then((cache) => {
          return cache.match(event.request)
            .then((cached) => {
              if (cached) {
                return cached;
              }

              return fetch(event.request)
                .then((response) => {
                  if (response.ok) {
                    cache.put(event.request, response.clone());
                  }
                  return response;
                });
            });
        })
    );
    return;
  }

  // Static assets - cache first, network fallback
  event.respondWith(
    caches.match(event.request)
      .then((cached) => {
        if (cached) {
          // Return cached version immediately
          // Also fetch from network in background to update cache
          event.waitUntil(
            fetch(event.request)
              .then((response) => {
                if (response.ok) {
                  caches.open(STATIC_CACHE)
                    .then((cache) => cache.put(event.request, response));
                }
              })
              .catch(() => {}) // Ignore network errors for background update
          );

          return cached;
        }

        // Not in cache, fetch from network
        return fetch(event.request)
          .then((response) => {
            // Cache successful responses for static files
            if (response.ok && shouldCache(event.request)) {
              const responseClone = response.clone();
              caches.open(STATIC_CACHE)
                .then((cache) => cache.put(event.request, responseClone));
            }
            return response;
          });
      })
  );
});

// Determine if a request should be cached
function shouldCache(request) {
  const url = new URL(request.url);

  // Cache same-origin static files
  if (url.origin === self.location.origin) {
    return true;
  }

  // Cache CDN resources (Phaser, etc.)
  if (url.hostname.includes('cdn.jsdelivr.net')) {
    return true;
  }

  return false;
}

// Message handling for cache management
self.addEventListener('message', (event) => {
  if (event.data.type === 'PRECACHE_AUDIO') {
    // Precache audio files during splash screen
    const audioUrls = event.data.urls || [];

    caches.open(AUDIO_CACHE)
      .then((cache) => {
        return Promise.all(
          audioUrls.map((url) => {
            return fetch(url)
              .then((response) => {
                if (response.ok) {
                  return cache.put(url, response);
                }
              })
              .catch(() => {
                console.warn('[SW] Failed to precache:', url);
              });
          })
        );
      })
      .then(() => {
        // Notify client that precaching is complete
        event.ports[0]?.postMessage({ type: 'PRECACHE_COMPLETE' });
      });
  }

  if (event.data.type === 'CLEAR_CACHE') {
    caches.keys()
      .then((names) => Promise.all(names.map((n) => caches.delete(n))))
      .then(() => {
        event.ports[0]?.postMessage({ type: 'CACHE_CLEARED' });
      });
  }

  if (event.data.type === 'GET_CACHE_SIZE') {
    getCacheSize()
      .then((size) => {
        event.ports[0]?.postMessage({ type: 'CACHE_SIZE', size });
      });
  }
});

// Calculate total cache size
async function getCacheSize() {
  const cacheNames = await caches.keys();
  let totalSize = 0;

  for (const name of cacheNames) {
    const cache = await caches.open(name);
    const keys = await cache.keys();

    for (const request of keys) {
      const response = await cache.match(request);
      if (response) {
        const blob = await response.blob();
        totalSize += blob.size;
      }
    }
  }

  return totalSize;
}

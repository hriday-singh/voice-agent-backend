// Service Worker for CAW Voice Agent Portal

// Cache name with version
const CACHE_NAME = "caw-portal-cache-v1";

// Assets to cache initially - most importantly the logo files
const STATIC_ASSETS = [
  "/assets/caw-tech-logo.gif",
  "/assets/caw-tech-logo.svg",
  "/favicon.ico",
  "/logo.svg",
  "/cropped-fav-icon-32x32.png",
];

// Install event - cache static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => {
        console.log("Opened cache");
        return cache.addAll(STATIC_ASSETS);
      })
      .catch((error) => {
        console.error("Failed to cache static assets:", error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => {
            return cacheName !== CACHE_NAME;
          })
          .map((cacheName) => {
            return caches.delete(cacheName);
          })
      );
    })
  );
});

// Fetch event - serve from cache or fetch from network
self.addEventListener("fetch", (event) => {
  // For non-GET requests, go to network
  if (event.request.method !== "GET") {
    return;
  }

  // For logo assets, prioritize cache
  const url = new URL(event.request.url);
  const isLogoAsset = STATIC_ASSETS.some(
    (asset) =>
      url.pathname.endsWith(asset) || url.pathname.includes("caw-tech-logo")
  );

  if (isLogoAsset) {
    event.respondWith(
      caches.match(event.request).then((response) => {
        // Return the cached response if we have it
        if (response) {
          return response;
        }

        // Otherwise fetch from network and cache
        return fetch(event.request).then((networkResponse) => {
          // Don't cache non-successful responses
          if (!networkResponse || networkResponse.status !== 200) {
            return networkResponse;
          }

          // Cache the successful response
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });

          return networkResponse;
        });
      })
    );
  } else {
    // For other assets, use network first, then cache
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(event.request);
      })
    );
  }
});

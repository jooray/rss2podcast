self.addEventListener('install', function(event) {
  event.waitUntil(
      caches.open('rss2podcast-cache-v1')
      .then(function(cache) {
          console.log('Opened cache');
          return cache.addAll([
              '/',
              '/static/style.css',
              '/static/manifest.json',
              '/static/icons/icon-192x192.png',
              '/static/icons/icon-512x512.png'
          ]);
      })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
      caches.match(event.request)
      .then(function(response) {
          // Cache hit - return response
          if (response) {
              return response;
          }
          return fetch(event.request);
      })
  );
});

const CACHE_NAME = 'jex-fuel-cache-v1.3.0';
const ASSETS_TO_CACHE = [
    './',
    './index.html',
    './styles_pwa.css',
    './manifest.json',
    './assets/logo_jex.png',
    './assets/logo_jex.ico'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('SW: Pre-cacheando App Shell de JEX Fuel...');
            return Promise.allSettled(
                ASSETS_TO_CACHE.map((url) => 
                    cache.add(url).catch((err) => console.warn(`SW: No se pudo precachear ${url}:`, err))
                )
            );
        }).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        console.log('SW: Eliminando caché obsoleta:', cache);
                        return caches.delete(cache);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const request = event.request;

    if (request.method !== 'GET') {
        return;
    }

    if (request.url.includes('/api/')) {
        return;
    }

    event.respondWith(
        caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {

                fetch(request).then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        caches.open(CACHE_NAME).then((cache) => cache.put(request, networkResponse));
                    }
                }).catch(() => {});
                return cachedResponse;
            }
            return fetch(request);
        })
    );
});
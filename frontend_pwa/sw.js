const CACHE_NAME = 'jex-fuel-cache-v1';
const ASSETS_TO_CACHE = [
    './index.html',
    './styles_pwa.css',
    './manifest.json',
    './assets/logo_jex.png',
    './assets/logo_jex.ico'
];

// 1. Evento de instalación: Guarda los archivos en el almacenamiento interno del dispositivo
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('SW: Archivos estáticos de JEX guardados en caché con éxito.');
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
});

// 2. Evento de activación: Limpia cachés antiguas si actualizas la versión de la app
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        console.log('SW: Limpiando caché obsoleta.');
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
});

// 3. Interceptador de peticiones: Si el supervisor no tiene red, sirve los archivos locales guardados
self.addEventListener('fetch', (event) => {
    // Solo interceptamos recursos locales, no llamadas externas de la API de FastAPI
    if (!event.request.url.startsWith(self.location.origin)) return;

    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(event.request);
        })
    );
});

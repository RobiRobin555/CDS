self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Bypass any dev specific requests like /@vite/client
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/@vite')) {
    return; // Let it 404 instead of caching or redirecting
  }
  // Default: passthrough
  event.respondWith(fetch(event.request).catch(() => new Response('', { status: 503 })));
});
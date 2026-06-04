// SDACS Service Worker — Phase 9 MOB
// 정적 자산 캐싱 + 오프라인 동작 (시뮬레이터 핵심 파일만)
const CACHE = 'sdacs-v1-2026-06-04';
const PRECACHE = [
  'swarm_3d_simulator.html',
  'maritime_detection_simulator.html',
  'manifest.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) =>
      cache.addAll(PRECACHE).catch(() => { /* CDN/외부 리소스 일부 실패 허용 */ })
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  // Cache-first 전략 (HTML/JS/CSS)
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req)
        .then((resp) => {
          if (!resp || resp.status !== 200 || resp.type === 'opaque') return resp;
          const clone = resp.clone();
          caches.open(CACHE).then((c) => c.put(req, clone)).catch(() => {});
          return resp;
        })
        .catch(() => cached || new Response('Offline', { status: 503 }));
    })
  );
});

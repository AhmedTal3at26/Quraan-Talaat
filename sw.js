/* Service worker: يخزّن ملفات التطبيق وصفحات المصحف مؤقتًا. */

const VERSION = 'qt-v6';
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './css/app.css',
  './js/app.js',
  './js/data.js',
  './js/pagesource.js',
  './vendor/pdf.min.mjs',
  './vendor/pdf.worker.min.mjs',
  './data/surahs.json',
  './data/verses-uthmani.json',
  './data/juz.json',
  './data/mushaf-index.json',
  './icons/icon.svg'
];

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(VERSION);
    await c.addAll(SHELL.map(u => new Request(u, { cache: 'reload' })));
    // سيطر فورًا على الصفحة المفتوحة حتى لا تخدم نسخة قديمة
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  const isPdf = url.pathname.includes('/assets/mushaf/');
  const isPageImg = /\/pages\/\d+\.webp$/.test(url.pathname);
  const isThumb = /\/thumbs\/\d+\.webp$/.test(url.pathname);

  if (isPdf || isPageImg || isThumb){
    // cache-first: these never change
    e.respondWith((async () => {
      const c = await caches.open(VERSION + '-pages');
      const hit = await c.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok) c.put(req, res.clone());
      return res;
    })());
    return;
  }

  // ملفات التطبيق: الشبكة أولًا (تحديث فوري) مع الذاكرة كبديل عند انقطاع الشبكة
  e.respondWith((async () => {
    const c = await caches.open(VERSION);
    try {
      const res = await fetch(req, { cache: 'no-cache' });
      if (res.ok) c.put(req, res.clone());
      return res;
    } catch {
      const hit = await c.match(req);
      if (hit) return hit;
      throw new Error('offline and not cached');
    }
  })());
});
/* Service worker seminimal mungkin.
 *
 * Tugasnya hanya dua: membuat aplikasi memenuhi syarat dipasang sebagai PWA,
 * dan menampilkan kerangka halaman saat jaringan putus.
 *
 * Yang DISENGAJA tidak dilakukan: menyentuh /api sama sekali. Cache sudah dua
 * kali menggigit proyek ini - klip gTTS lama terus diputar walau berkasnya sudah
 * diganti - jadi jawaban, klip, dan seluruh lalu lintas API dilewatkan apa adanya.
 */
// v2 (20-11): ikon diganti dengan logo SayIt milik landing page. Nama cache
// WAJIB ikut naik setiap kali isi berkas di KERANGKA berubah tanpa ganti nama -
// `activate` hanya menghapus cache yang namanya BERBEDA, jadi dengan nama yang
// sama ikon lama akan tetap tersimpan dan terpakai saat luring.
const CACHE = 'sayit-kerangka-v2';
const KERANGKA = ['/', '/manifest.json', '/icon-192.png', '/icon-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(KERANGKA)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((k) => Promise.all(k.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // API tidak pernah disentuh: biarkan peramban menanganinya sendiri.
  if (url.pathname.startsWith('/api') || e.request.method !== 'GET') return;

  // Halaman: jaringan dulu, kerangka tersimpan hanya kalau jaringannya putus.
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => caches.match('/')));
    return;
  }
  if (KERANGKA.includes(url.pathname)) {
    e.respondWith(fetch(e.request).catch(() => caches.match(url.pathname)));
  }
});

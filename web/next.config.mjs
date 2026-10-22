// API dilewatkan rewrite supaya satu origin dengan frontend: tidak perlu CORS,
// dan panel peramban / perangkat lain tidak perlu tahu alamat backend.
// Produksi: set API_ORIGIN ke URL Hugging Face Space di Vercel.
const nextConfig = {
  experimental: {
    /* Batas waktu proxy rewrite. Bawaan Next 30 detik, dan modul kedaluwarsa
       MELEWATINYA: terukur 54,8 detik untuk satu foto yang memicu percobaan
       rotasi, dengan p90 72,9 detik dan maksimum 99,2 detik di 16 kemasan.

       Gejalanya menyesatkan: server menjawab 200 dengan benar (terlihat di
       lognya), tetapi proxy sudah menyerah lebih dulu dan membalas teks biasa
       "Internal Server Error". Klien tidak bisa mengurainya sebagai JSON SayIt
       lalu mengumumkan "tidak bisa menghubungi server" - padahal servernya
       baik-baik saja dan masih bekerja. Uang (1,4 s) dan dokumen (11,5 s) tidak
       pernah kena, jadi hanya kedaluwarsa yang tampak rusak.

       180 detik memberi jarak di atas maksimum terukur. Ini BUKAN izin untuk
       membiarkan latensi tumbuh - penyimpangan NFR-01 tetap tercatat. */
    proxyTimeout: 180_000,
  },
  async rewrites() {
    const api = process.env.API_ORIGIN || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
};
export default nextConfig;

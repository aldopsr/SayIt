// API dilewatkan rewrite supaya satu origin dengan frontend: tidak perlu CORS,
// dan panel peramban / perangkat lain tidak perlu tahu alamat backend.
// Produksi: set API_ORIGIN ke URL Hugging Face Space di Vercel.
const nextConfig = {
  async rewrites() {
    const api = process.env.API_ORIGIN || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
};
export default nextConfig;

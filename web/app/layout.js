import "./globals.css";

export const metadata = {
  title: "SayIt",
  description: "Potret, tanya dengan suara, dengar jawabannya.",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "SayIt" },
  /* iOS TIDAK membaca `icons` dari manifest untuk ikon layar utama - ia hanya
     memakai <link rel="apple-touch-icon">. Tanpa baris ini, "Tambah ke Layar
     Utama" di iPhone memasang ikon berupa TANGKAPAN LAYAR halaman. Berkasnya
     berlatar penuh dan tanpa transparansi, karena iOS mengomposit area
     transparan ke hitam lalu membulatkan sendiri sudutnya. */
  icons: {
    icon: [{ url: "/icon-192.png", sizes: "192x192", type: "image/png" }],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
};

export const viewport = {
  themeColor: "#050809",
  viewportFit: "cover",
  width: "device-width",
  initialScale: 1,
  // maximumScale sengaja TIDAK diset: mengunci zoom adalah anti-pola
  // aksesibilitas (WCAG 1.4.4). Penggunanya tunanetra, tetapi low vision juga
  // memakai aplikasi ini dan mereka perlu bisa memperbesar.
};

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}

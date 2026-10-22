import "./globals.css";

export const metadata = {
  title: "SayIt",
  description: "Potret, tanya dengan suara, dengar jawabannya.",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "SayIt" },
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

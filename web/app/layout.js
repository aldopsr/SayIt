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
  maximumScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}

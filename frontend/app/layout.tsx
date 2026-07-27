import type { Metadata } from "next";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import "./globals.css";

// System-font stack — no network fetch, no build-time Google Fonts dependency.
// Same CSS variable names so all existing Tailwind classes (font-sans/font-mono) keep working.
const FONT_VARS =
  "[--font-inter:ui-sans-serif,system-ui,-apple-system,Segoe_UI,Roboto,Helvetica,Arial,sans-serif] " +
  "[--font-jetbrains:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation_Mono','Courier_New',monospace]";

export const metadata: Metadata = {
  title: "HACK — Hedera Agent Commerce Kit",
  description:
    "The infrastructure for building x402-paid AI services on Hedera. One decorator. Mirror Node verification. HCS receipts. Compliance certification. Production-ready.",
  metadataBase: new URL("https://hack.dev"),
  openGraph: {
    title: "HACK — Hedera Agent Commerce Kit",
    description: "The infrastructure for building x402-paid AI services on Hedera.",
    type: "website",
  },
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={FONT_VARS}>
      <body className="min-h-screen bg-background text-text-primary antialiased">
        <Navbar />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}

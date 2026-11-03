import type { Metadata } from "next";
import { IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { DemoBanner } from "@/components/DemoBanner";

const ibmPlexMono = IBM_Plex_Mono({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title:
    process.env.NEXT_PUBLIC_DEMO_MODE === "1"
      ? "Unsaid: read-only demo of semantic 10-K disclosure analysis"
      : "Unsaid — Semantic 10-K Disclosure Analysis",
  description:
    "Surface what companies quietly removed or softened in their annual risk disclosures. Semantic year-over-year 10-K diff.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${ibmPlexMono.variable} h-full`}>
      <body className="min-h-full flex flex-col bg-[var(--background)] text-zinc-100 font-mono antialiased">
        <DemoBanner />
        {children}
      </body>
    </html>
  );
}

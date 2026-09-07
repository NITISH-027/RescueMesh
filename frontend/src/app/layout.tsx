import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RescueMesh // Tactical Geospatial Triage Command",
  description: "AI-powered rapid damage & flood triage for post-hurricane satellite imagery",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0A0B0E] text-zinc-100 min-h-screen antialiased flex flex-col font-sans selection:bg-zinc-700 selection:text-white overflow-hidden">
        {children}
      </body>
    </html>
  );
}

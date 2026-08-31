import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { AppShell } from "@/components/layout/AppShell";

import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MLB Analytics Dashboard",
  description: "Player and team analytics, forecasts, and season leaderboards.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased bg-[#121212] text-gray-200`}>
        <AppShell>
          {children}
        </AppShell>
      </body>
    </html>
  );
}

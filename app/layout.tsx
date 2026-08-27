import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { TopNav } from "@/components/nav/TopNav";

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
      <body className={`${inter.variable} font-sans antialiased`}>
        <TopNav />
        <main className="mx-auto max-w-[1280px] px-xl py-xxl">{children}</main>
      </body>
    </html>
  );
}

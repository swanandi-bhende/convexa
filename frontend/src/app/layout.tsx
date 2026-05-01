import type { Metadata } from "next";
import { MainLayout } from "@/components/MainLayout";
import "./globals.css";

export const metadata: Metadata = {
  title: "Convexa - Market Debate Platform",
  description:
    "Autonomous AI debate platform for market analysis and price discovery powered by Bull and Bear agents",
  viewport: "width=device-width, initial-scale=1",
  robots: "index, follow",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <head>
        <meta charSet="utf-8" />
        <meta name="theme-color" content="#ffffff" />
      </head>
      <body className="h-full bg-background text-text-primary antialiased">
        <MainLayout>{children}</MainLayout>
      </body>
    </html>
  );
}

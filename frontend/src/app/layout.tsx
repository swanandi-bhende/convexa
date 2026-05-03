import type { Metadata } from "next";
import { Manrope, Work_Sans, IBM_Plex_Mono } from "next/font/google";
import { Providers } from "@/components/Providers";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import "./globals.css";

const displayFont = Manrope({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
});

const bodyFont = Work_Sans({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
});

const monoFont = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Convexa",
  description: "Autonomous market debate dashboard with live conviction tracking.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${displayFont.variable} ${bodyFont.variable} ${monoFont.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>
          <Header />
          <div className="mx-auto flex w-full max-w-[1400px] flex-1">
            <Sidebar />
            <main className="w-full px-6 py-8 lg:px-10 lg:py-10">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}

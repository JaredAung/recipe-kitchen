import type { Metadata } from "next";
import { Barlow_Condensed, Noto_Sans_Myanmar, Source_Serif_4 } from "next/font/google";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

import "./globals.css";

const display = Barlow_Condensed({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-barlow",
});

const body = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source",
});

const myanmar = Noto_Sans_Myanmar({
  subsets: ["myanmar"],
  weight: ["400", "600"],
  variable: "--font-noto-myanmar",
});

export const metadata: Metadata = {
  title: "Recipe Kitchen",
  description:
    "Paste a cooking reel. Cook from the card. Works for video recipes in Burmese and English.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${body.variable} ${myanmar.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-soapstone font-body text-cast-iron">
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}

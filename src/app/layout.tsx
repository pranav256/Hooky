import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hooky — Autonomous AI Video Clipper | Free & Open-Source Opus Clip Alternative",
  description: "100% Free and Open-Source (MIT) autonomous AI video clipper. Turn long YouTube videos, podcasts, and interviews into high-retention vertical 9:16 Shorts, Reels, and TikToks with Google Gemini 2.0 Flash semantic narrative detection, faster-whisper animated captions, and local GPU FFmpeg encoding.",
  keywords: ["Hooky", "AI video clipper", "open source opus clip alternative", "klap alternative", "vertical video generator", "youtube shorts generator", "instagram reels generator", "faster-whisper", "gemini 2.0", "ffmpeg 9:16", "hormozi captions", "free video clipper"],
  authors: [{ name: "Pranav / Hooky Contributors" }],
  openGraph: {
    type: "website",
    url: "https://github.com/pranav256/Hooky",
    siteName: "Hooky",
    title: "Hooky — Autonomous AI Video Clipper & Shorts/Reels Generator",
    description: "Open-source Opus Clip alternative. Turn long videos into high-retention 9:16 vertical shorts locally with Gemini 2.0 Flash semantic detection, faster-whisper animated captions, and local GPU acceleration.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Hooky — Autonomous AI Video Clipper & Shorts/Reels Generator",
    description: "Free & open-source Opus Clip alternative. Local GPU rendering, faster-whisper animated subtitles, and Gemini 2.0 hook detection.",
  },
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              "name": "Hooky",
              "applicationCategory": "MultimediaApplication",
              "operatingSystem": "Linux, macOS, Windows",
              "isAccessibleForFree": true,
              "license": "https://opensource.org/licenses/MIT",
              "description": "Autonomous AI video clipper and shorts/reels generator. Open-source Opus Clip alternative powered by Google Gemini 2.0 Flash, faster-whisper, and FFmpeg.",
              "url": "https://github.com/pranav256/Hooky",
              "codeRepository": "https://github.com/pranav256/Hooky",
              "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD",
                "description": "100% Free & Open Source under MIT License"
              }
            }),
          }}
        />
      </head>
      <body className="antialiased bg-[#080A0F] text-[#F1F5F9] selection:bg-[#E5C07B]/30 selection:text-white">
        {children}
        <Analytics />
      </body>
    </html>
  );
}

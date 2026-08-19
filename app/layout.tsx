import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://girrj.github.io"),
  title: "Threat & Thesis",
  description: "공식 보안 권고와 AI 연구를 확인해 실무에 필요한 내용만 한국어로 정리합니다.",
  openGraph: {
    title: "Threat & Thesis",
    description: "보안·AI 브리핑 — 원문을 확인한 자료와 실무 맥락",
    type: "website",
    url: "https://girrj.github.io/threat-and-thesis/",
    images: [
      {
        url: "https://girrj.github.io/threat-and-thesis/og.png",
        width: 1732,
        height: 908,
        alt: "Threat & Thesis 보안·AI 브리핑",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Threat & Thesis",
    description: "보안·AI 브리핑 — 원문을 확인한 자료와 실무 맥락",
    images: ["https://girrj.github.io/threat-and-thesis/og.png"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://girrj.github.io"),
  title: "Threat & Thesis",
  description: "검증한 보안 위협과 AI 연구를 분야별 순위와 선정 근거로 정리합니다.",
  openGraph: {
    title: "Threat & Thesis",
    description: "분야별 보안·AI 리서치 — 원문을 확인한 자료와 선정 근거",
    type: "website",
    url: "https://girrj.github.io/threat-and-thesis/",
    images: [
      {
        url: "https://girrj.github.io/threat-and-thesis/og.png",
        width: 1732,
        height: 908,
        alt: "Threat & Thesis 분야별 보안·AI 리서치",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Threat & Thesis",
    description: "분야별 보안·AI 리서치 — 원문을 확인한 자료와 선정 근거",
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

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Threat & Thesis",
  description: "정보보안 권고, AI 보안 동향, 최신 논문과 기술 업데이트를 모아 보는 인텔리전스 허브",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "TokenMall 控制台",
  description: "Token 售卖与 API 管理平台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

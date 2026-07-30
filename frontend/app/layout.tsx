import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "V-ID | Xác minh danh tính",
  description: "Luồng xác minh danh tính an toàn của V-ID",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}

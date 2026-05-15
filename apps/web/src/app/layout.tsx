import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Solo",
  description: "Plan flexible long-weekend trips from your home city.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

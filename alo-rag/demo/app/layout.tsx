import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ALO Yoga RAG Assistant",
  description:
    "AI-powered assistant for ALO Yoga product, policy, and customer queries",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="h-dvh">{children}</body>
    </html>
  );
}

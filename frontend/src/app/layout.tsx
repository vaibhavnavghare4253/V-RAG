import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "AdaptiveDocAI - Adaptive Multimodal RAG with Uncertainty Awareness",
  description: "Enterprise-grade multimodal document question answering system with dynamic evidence retrieval and calibrated uncertainty estimation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="flex min-h-screen flex-col bg-background text-gray-100 antialiased">
        <Navbar />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-gray-900 py-6 text-center text-xs text-gray-500">
          AdaptiveDocAI — Research Platform for Multimodal Document Intelligence & Calibrated Uncertainty
        </footer>
      </body>
    </html>
  );
}


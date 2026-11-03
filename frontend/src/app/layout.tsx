import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ParkSense AI — Smart Parking Detection",
  description:
    "AI-powered parking lot analysis: detect vehicles, estimate capacity, and visualize empty spaces.",
  keywords: ["parking", "AI", "computer vision", "YOLO", "smart city"],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="noise min-h-screen bg-surface-0 antialiased">
        {children}
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SAT Oracle Builder",
  description: "Quantum SAT Solver using Grover's Algorithm",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  );
}

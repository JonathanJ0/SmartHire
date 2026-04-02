import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { RoleBasedNav } from "@/components/RoleBasedNav";

export const metadata: Metadata = {
  title: "UmaMaj – Interview Evaluation",
  description: "AI-powered interview practice and evaluation for candidates and interviewers",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased min-h-screen">
        <header className="border-b border-[var(--color-border)] bg-[var(--color-surface-elevated)]">
          <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
            <Link href="/" className="font-semibold text-lg text-[var(--color-primary)]">
              SmartHire
            </Link>
            <RoleBasedNav />
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}

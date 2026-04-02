import type { Metadata } from "next";
import "./globals.css";

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
            <a href="/" className="font-semibold text-lg text-[var(--color-primary)]">
              SmartHire
            </a>
            <div className="flex gap-4">
              <a
                href="/interviewee/resume"
                className="text-sm text-[var(--color-muted)] hover:text-[var(--color-primary)]"
              >
                Interviewee
              </a>
              <a
                href="/interviewer"
                className="text-sm text-[var(--color-muted)] hover:text-[var(--color-primary)]"
              >
                Interviewer
              </a>
            </div>
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}

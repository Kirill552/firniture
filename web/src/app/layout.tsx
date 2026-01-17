import type { Metadata } from "next";
import { ErrorBoundary } from "@/components/error-boundary";
import { Onest } from "next/font/google";
import "./globals.css";
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import QueryProvider from "@/components/query-provider";
import AuthLayout from "@/components/auth-layout";
import { AnimatedLayout } from "@/components/animated-layout";
import { Toaster } from "@/components/ui/toaster";
import { ThemeProvider } from "@/components/theme-provider";
import { DebugOverlay } from "@/components/debug-overlay";

const onest = Onest({
  subsets: ["latin", "cyrillic"],
  variable: "--font-onest",
  display: 'swap',
  weight: ["300", "400", "500", "600", "700"],
})

export const metadata: Metadata = {
  title: "Мебель-ИИ",
  description: "Облачный AI-SaaS для мебельных фабрик",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body className={`${onest.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem={false}
          disableTransitionOnChange
        >
          <QueryProvider>
            <ErrorBoundary>
              <AuthLayout>
                {/* AnimatedLayout отключен для отладки блокировки BOM */}
                {/* <AnimatedLayout> */}
                  {children}
                {/* </AnimatedLayout> */}
              </AuthLayout>
            </ErrorBoundary>
            <ReactQueryDevtools initialIsOpen={false} />
            <Toaster />
            <DebugOverlay />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

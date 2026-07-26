import type { Metadata } from "next";
import { AnalyticsProvider } from "@/components/analytics/analytics-provider";
import { AnalyticsConsent } from "@/components/analytics/analytics-consent";
import { FeatureFlagsProvider } from "@/features/mvp";
import { ErrorBoundary } from "@/components/error-boundary";
import { Onest } from "next/font/google";
import "./globals.css";
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import QueryProvider from "@/components/query-provider";
import AuthLayout from "@/components/auth-layout";
import { AnimatedLayout } from "@/components/animated-layout";
import { Toaster } from "@/components/ui/toaster";
import { ThemeProvider } from "@/components/theme-provider";

const onest = Onest({
  subsets: ["latin", "cyrillic"],
  variable: "--font-onest",
  display: 'swap',
  weight: ["300", "400", "500", "600", "700"],
})

export const metadata: Metadata = {
  title: "АвтоРаскрой",
  description: "Умный раскрой и присадка для мебельных фабрик",
  // Верификация вебмастеров (Яндекс + Google Search Console)
  other: {
    "yandex-verification": "85f3807d99849b7b",
    "google-site-verification": "cmNCi3VhuOG1AwFtdorLt6AP-cFfZVLGZ0MiTeCynbI",
  },
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
            <FeatureFlagsProvider>
              <AnalyticsProvider>
                <ErrorBoundary>
                  <AuthLayout>
                    {/* AnimatedLayout отключен для отладки блокировки BOM */}
                    {/* <AnimatedLayout> */}
                      {children}
                    {/* </AnimatedLayout> */}
                  </AuthLayout>
                </ErrorBoundary>
                <AnalyticsConsent />
              </AnalyticsProvider>
            </FeatureFlagsProvider>
            <ReactQueryDevtools initialIsOpen={false} />
            <Toaster />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

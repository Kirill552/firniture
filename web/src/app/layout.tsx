import type { Metadata } from "next";
import { AnalyticsProvider } from "@/components/analytics/analytics-provider";
import { AnalyticsConsent } from "@/components/analytics/analytics-consent";
import { YandexMetrika } from "@/components/analytics/yandex-metrika";
import { Suspense } from "react";
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
  metadataBase: new URL("https://avtoraskroy.ru"),
  title: {
    default: "АвтоРаскрой — эскиз в точный заказ",
    template: "%s — АвтоРаскрой",
  },
  description:
    "Загрузите фото или PDF эскиза: сервис снимет размеры, соберёт спецификацию и выдаст DXF с присадкой и PDF карты раскроя. Первый заказ бесплатно.",
  openGraph: {
    type: "website",
    locale: "ru_RU",
    url: "https://avtoraskroy.ru",
    siteName: "АвтоРаскрой",
    title: "Эскиз клиента — в точный заказ",
    description:
      "Фото наброска превращается в спецификацию, DXF с точками присадки и карту раскроя. Первый заказ бесплатно, дальше 890 ₽ за заказ.",
    images: [
      {
        url: "/og.jpg",
        width: 1200,
        height: 630,
        alt: "АвтоРаскрой: эскиз превращается в точный заказ",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Эскиз клиента — в точный заказ",
    description:
      "Спецификация, DXF с присадкой и карта раскроя из фото наброска. Первый заказ бесплатно.",
    images: ["/og.jpg"],
  },
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
                <Suspense fallback={null}>
                  <YandexMetrika />
                </Suspense>
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

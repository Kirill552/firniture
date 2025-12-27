import type { Metadata } from "next";
import { ErrorBoundary } from "@/components/error-boundary";
import { Inter } from "next/font/google";
import "./globals.css";
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import QueryProvider from "@/components/query-provider";
import AuthLayout from "@/components/auth-layout";
import { AnimatedLayout } from "@/components/animated-layout";
import { Toaster } from "@/components/ui/toaster";
import { ThemeProvider } from "@/components/theme-provider";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter",
  display: 'swap',
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
      <body className={`${inter.variable} antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <QueryProvider>
            <ErrorBoundary>
              <AuthLayout>
                <AnimatedLayout>
                  {children}
                </AnimatedLayout>
              </AuthLayout>
            </ErrorBoundary>
            <ReactQueryDevtools initialIsOpen={false} />
            <Toaster />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

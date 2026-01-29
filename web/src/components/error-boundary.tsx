"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
          <div className="text-destructive mb-4">
            <AlertTriangle className="h-12 w-12 mx-auto" />
          </div>
          <h2 className="text-2xl font-bold mb-2">Что-то пошло не так</h2>
          <p className="text-muted-foreground mb-6 max-w-md">
            Произошла ошибка при загрузке компонента. Попробуйте обновить страницу или перезайти в систему.
          </p>
          <div className="flex gap-2">
            <Button onClick={() => window.location.reload()}>Обновить страницу</Button>
            <Button variant="outline" onClick={() => window.location.href = "/orders"}>
              На главную
            </Button>
          </div>
          {this.state.error && (
            <details className="mt-6 p-4 border rounded-md bg-destructive/5 text-sm">
              <summary className="cursor-pointer font-medium">Детали ошибки</summary>
              <pre className="mt-2 text-destructive whitespace-pre-wrap">
                {this.state.error.message}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
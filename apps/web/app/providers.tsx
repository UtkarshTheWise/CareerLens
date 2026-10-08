"use client";
import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { MotionConfig } from "framer-motion";
import { shouldRetryQuery } from "@/lib/api/transport";
import { AuthProvider } from "@/components/auth/auth-provider";
export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient({ defaultOptions: {
    queries: { staleTime: 30_000, retry: shouldRetryQuery, refetchOnWindowFocus: false },
    mutations: { retry: false },
  }}));
  return <ThemeProvider attribute="data-theme" defaultTheme="system" enableSystem disableTransitionOnChange>
    <QueryClientProvider client={client}><AuthProvider><MotionConfig reducedMotion="user">{children}</MotionConfig></AuthProvider></QueryClientProvider>
  </ThemeProvider>;
}

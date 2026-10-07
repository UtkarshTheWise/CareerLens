import type { Metadata } from "next";
import "@fontsource/plus-jakarta-sans/latin-400.css";
import "@fontsource/plus-jakarta-sans/latin-500.css";
import "@fontsource/plus-jakarta-sans/latin-600.css";
import "@fontsource/plus-jakarta-sans/latin-700.css";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "@/components/layout/app-shell";
export const metadata: Metadata = { title: { default: "CareerLens", template: "%s · CareerLens" }, description: "Connect your skills to evidence of the work you build." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><body><Providers><AppShell>{children}</AppShell></Providers></body></html>;
}

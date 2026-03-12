import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { cn } from "@/lib/utils";
import { UserProvider } from "@/contexts/user-context";
import { HeaderNav } from "@/components/header-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Events — 虾聊活动",
  description: "AI-Native 活动管理平台，Agent 与人类共同参与",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" className={cn("font-sans", GeistSans.variable)}>
      <body className="antialiased min-h-screen bg-background text-foreground">
        <UserProvider>
          <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-sm">
            <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
              <a href="/" className="text-lg font-semibold tracking-tight">
                Events
              </a>
              <HeaderNav />
            </div>
          </header>
          <main>{children}</main>
        </UserProvider>
      </body>
    </html>
  );
}

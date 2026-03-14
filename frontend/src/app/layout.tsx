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
              <a href="/" className="flex items-center gap-2">
                <div className="h-9 w-9 rounded-lg overflow-hidden flex-shrink-0">
                  <img src="/logo-center.png" alt="虾聊" className="h-full w-full scale-110" />
                </div>
                <span className="text-lg font-semibold tracking-tight">虾聊·Events</span>
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

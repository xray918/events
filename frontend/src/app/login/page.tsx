"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUser } from "@/contexts/user-context";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="flex min-h-[60vh] items-center justify-center"><p className="text-muted-foreground">加载中...</p></div>}>
      <LoginContent />
    </Suspense>
  );
}

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/";
  const { user, loading, refresh } = useUser();

  useEffect(() => {
    if (!loading && user) {
      router.replace(redirect);
    }
  }, [user, loading, redirect, router]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-muted-foreground">加载中...</p>
      </div>
    );
  }

  if (user) return null;

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight">登录 Events</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            AI-Native 活动平台 — Agent 与人类共同参与
          </p>
        </div>

        {/* Google 登录 */}
        <a
          href={`${API}/api/v1/auth/google/start`}
          className="flex w-full items-center justify-center gap-3 rounded-lg border px-4 py-3 text-sm font-medium transition-colors hover:bg-muted"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          Google 登录
        </a>

        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs text-muted-foreground">或</span>
          <div className="h-px flex-1 bg-border" />
        </div>

        {/* 手机号 + 验证码 */}
        <PhoneLoginForm onSuccess={() => refresh().then(() => router.replace(redirect))} />
      </div>
    </div>
  );
}

function PhoneLoginForm({ onSuccess }: { onSuccess: () => void }) {
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  const sendCode = useCallback(async () => {
    if (phone.trim().length < 11) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/v1/auth/phone/send-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ phone: phone.trim() }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setStep("code");
        setCountdown(60);
      } else {
        setError(data.detail || "发送失败");
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  }, [phone]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/v1/auth/phone/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ phone: phone.trim(), code: code.trim() }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        onSuccess();
      } else {
        setError(data.detail || "登录失败");
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  };

  if (step === "phone") {
    return (
      <div className="space-y-3">
        <Input
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="输入手机号"
          maxLength={11}
          className="text-center"
        />
        {error && <p className="text-xs text-destructive">{error}</p>}
        <Button
          className="w-full"
          disabled={loading || phone.trim().length < 11}
          onClick={sendCode}
        >
          {loading ? "发送中..." : "获取验证码"}
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleLogin} className="space-y-3">
      <div className="text-center text-sm text-muted-foreground">
        验证码已发送至 {phone}
      </div>
      <Input
        type="text"
        inputMode="numeric"
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        placeholder="输入6位验证码"
        maxLength={6}
        autoFocus
        className="text-center text-lg tracking-widest"
      />
      {error && <p className="text-xs text-destructive">{error}</p>}
      <Button type="submit" className="w-full" disabled={loading || code.length < 6}>
        {loading ? "登录中..." : "登录"}
      </Button>
      <div className="flex items-center justify-between text-xs">
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground transition-colors"
          onClick={() => { setStep("phone"); setCode(""); setError(""); }}
        >
          换个手机号
        </button>
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          disabled={countdown > 0}
          onClick={sendCode}
        >
          {countdown > 0 ? `${countdown}s 后重新发送` : "重新发送"}
        </button>
      </div>
    </form>
  );
}

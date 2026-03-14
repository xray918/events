"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import { SharePosterButton } from "./share-poster-button";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface CustomQuestion {
  id: string;
  question_text: string;
  question_type: string;
  options: string[] | null;
  is_required: boolean;
}

interface RegistrationInfo {
  id: string;
  status: string;
  qr_code_token: string;
  registered_via: string;
  registered_at: string;
  checked_in_at: string | null;
}

interface Props {
  slug: string;
  title?: string;
  questions?: CustomQuestion[] | null;
  eventStatus?: string;
  registrationDeadline?: string | null;
  capacity?: number | null;
  registrationCount?: number | null;
}

export function RegisterButton({ slug, title = "", questions, eventStatus, registrationDeadline, capacity, registrationCount }: Props) {
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [formError, setFormError] = useState("");
  const [result, setResult] = useState<{ success: boolean; message?: string } | null>(null);
  const [existingReg, setExistingReg] = useState<RegistrationInfo | null>(null);
  const [cancelLoading, setCancelLoading] = useState(false);

  const [showPhoneModal, setShowPhoneModal] = useState(false);
  const [phoneInput, setPhoneInput] = useState("");
  const [phoneCode, setPhoneCode] = useState("");
  const [phoneStep, setPhoneStep] = useState<"input" | "verify">("input");
  const [phoneLoading, setPhoneLoading] = useState(false);
  const [phoneError, setPhoneError] = useState("");
  const [countdown, setCountdown] = useState(0);
  const [pendingAnswers, setPendingAnswers] = useState<Record<string, string | string[]> | null>(null);

  const hasQuestions = questions && questions.length > 0;

  useEffect(() => {
    fetch(`${API}/api/v1/events/${slug}/registration`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        if (data.registered && data.data) {
          setExistingReg(data.data);
        }
      })
      .catch(() => {})
      .finally(() => setChecking(false));
  }, [slug]);

  const isDeadlinePassed = registrationDeadline
    ? new Date() > new Date(registrationDeadline)
    : false;

  const isFull = capacity && registrationCount != null
    ? registrationCount >= capacity
    : false;

  const isNotPublished = eventStatus && eventStatus !== "published";

  const statsText = `${registrationCount || 0} 人已报名${capacity ? ` · 限 ${capacity} 人` : ""}`;

  const ShareRow = () => (
    <div className="flex items-center gap-2">
      <SharePosterButton slug={slug} title={title} />
    </div>
  );

  if (checking) {
    return (
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{statsText}</p>
        <div className="h-9 w-24 animate-pulse rounded-lg bg-muted" />
      </div>
    );
  }

  if (existingReg) {
    const statusLabels: Record<string, string> = {
      approved: "已通过",
      pending: "待审批",
      waitlisted: "候补中",
      declined: "已拒绝",
      cancelled: "已取消",
    };
    const label = statusLabels[existingReg.status] || existingReg.status;

    if (existingReg.status === "cancelled") {
      return (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">{statsText}</p>
            <Button size="sm" onClick={() => { setExistingReg(null); setResult(null); }}>
              重新报名
            </Button>
          </div>
          <ShareRow />
        </div>
      );
    }

    const statusColor: Record<string, string> = {
      approved: "text-emerald-600",
      pending: "text-amber-600",
      waitlisted: "text-blue-600",
      declined: "text-destructive",
    };
    const colorClass = statusColor[existingReg.status] || "text-muted-foreground";
    const isCheckedIn = !!existingReg.checked_in_at;
    const statusText = isCheckedIn ? "✓ 已签到" : `✓ ${label}`;

    if (existingReg.status === "approved") {
      return (
        <div className="flex flex-col gap-3">
          {/* 统计 + 签到码（右上角主入口） */}
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">{statsText}</p>
            {!isCheckedIn ? (
              <Link href={`/checkin/${existingReg.qr_code_token}`}>
                <Button size="lg" className="font-semibold px-8">签到码</Button>
              </Link>
            ) : (
              <span className={`text-sm font-medium ${colorClass}`}>{statusText}</span>
            )}
          </div>
          {/* 状态标签 */}
          {!isCheckedIn && (
            <span className={`text-sm font-medium ${colorClass}`}>{statusText}</span>
          )}
          {/* 分享 + 取消报名 */}
          <div className="flex items-center justify-between gap-3">
            <ShareRow />
            {!isCheckedIn && (
              <button
                onClick={handleCancelRegistration}
                disabled={cancelLoading}
                className="text-xs text-muted-foreground hover:text-destructive transition-colors"
              >
                {cancelLoading ? "取消中..." : "取消报名"}
              </button>
            )}
          </div>
        </div>
      );
    }

    // pending / waitlisted / declined
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">{statsText}</p>
        </div>
        <span className={`text-sm font-medium ${colorClass}`}>{statusText}</span>
        <div className="flex items-center justify-between gap-3">
          <ShareRow />
          {existingReg.status !== "declined" && !isCheckedIn && (
            <button
              onClick={handleCancelRegistration}
              disabled={cancelLoading}
              className="text-xs text-muted-foreground hover:text-destructive transition-colors"
            >
              {cancelLoading ? "取消中..." : "取消报名"}
            </button>
          )}
        </div>
      </div>
    );
  }

  if (isNotPublished) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">{statsText}</p>
          <Button variant="secondary" disabled className="cursor-default">
            {{ draft: "未发布", cancelled: "已取消", completed: "已结束" }[eventStatus!] || eventStatus}
          </Button>
        </div>
        <ShareRow />
      </div>
    );
  }

  if (isDeadlinePassed) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">{statsText}</p>
          <Button variant="secondary" disabled className="cursor-default">报名已截止</Button>
        </div>
        <ShareRow />
      </div>
    );
  }

  if (isFull) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">{statsText}</p>
          <Button variant="secondary" disabled className="cursor-default">名额已满</Button>
        </div>
        <ShareRow />
      </div>
    );
  }

  if (result?.success) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">{statsText}</p>
          <Button variant="secondary" disabled className="cursor-default">
            {result.message}
          </Button>
        </div>
        <ShareRow />
      </div>
    );
  }

  async function handleCancelRegistration() {
    setCancelLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/events/${slug}/registration`, {
        method: "DELETE",
        credentials: "include",
      });
      const data = await res.json();
      if (data.success) {
        setExistingReg({ ...existingReg!, status: "cancelled" });
      }
    } catch {
      // ignore
    } finally {
      setCancelLoading(false);
    }
  }

  function handleClick() {
    if (hasQuestions) {
      setShowForm(true);
    } else {
      doRegister({});
    }
  }

  function updateAnswer(qId: string, value: string | string[]) {
    setAnswers((prev) => ({ ...prev, [qId]: value }));
  }

  function toggleMultiAnswer(qId: string, option: string) {
    setAnswers((prev) => {
      const current = (prev[qId] as string[]) || [];
      if (current.includes(option)) {
        return { ...prev, [qId]: current.filter((v) => v !== option) };
      }
      return { ...prev, [qId]: [...current, option] };
    });
  }

  function validateAndSubmit() {
    if (!questions) return;
    for (const q of questions) {
      if (q.is_required) {
        const val = answers[q.id];
        if (!val || (typeof val === "string" && !val.trim()) || (Array.isArray(val) && val.length === 0)) {
          setFormError(`请填写必填项：${q.question_text}`);
          return;
        }
      }
    }
    setFormError("");
    doRegister(answers);
  }

  async function doRegister(customAnswers: Record<string, string | string[]>) {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/events/${slug}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ custom_answers: Object.keys(customAnswers).length > 0 ? customAnswers : undefined }),
      });
      const data = await res.json();

      if (data.need_phone) {
        setPendingAnswers(customAnswers);
        setShowPhoneModal(true);
        setShowForm(false);
      } else if (data.success) {
        setResult({ success: true, message: data.data?.message || "报名成功！" });
        setShowForm(false);
        if (data.data) {
          setExistingReg({
            id: data.data.registration_id,
            status: data.data.status,
            qr_code_token: data.data.qr_code_token,
            registered_via: "web",
            registered_at: new Date().toISOString(),
            checked_in_at: null,
          });
        }
      } else {
        setResult({ success: false, message: data.detail || data.error || "报名失败" });
      }
    } catch {
      setResult({ success: false, message: "网络错误" });
    } finally {
      setLoading(false);
    }
  }

  function startCountdown() {
    setCountdown(60);
    const timer = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) { clearInterval(timer); return 0; }
        return c - 1;
      });
    }, 1000);
  }

  async function sendPhoneCode() {
    setPhoneError("");
    if (!/^1[3-9]\d{9}$/.test(phoneInput)) {
      setPhoneError("请输入有效的手机号");
      return;
    }
    setPhoneLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/auth/me/phone/send-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ phone: phoneInput }),
      });
      const data = await res.json();
      if (data.success) {
        setPhoneStep("verify");
        startCountdown();
      } else {
        setPhoneError(data.detail || "发送失败，请重试");
      }
    } catch {
      setPhoneError("网络错误");
    } finally {
      setPhoneLoading(false);
    }
  }

  async function bindPhone() {
    setPhoneError("");
    if (!phoneCode.trim()) {
      setPhoneError("请输入验证码");
      return;
    }
    setPhoneLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/auth/me/phone/bind`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ phone: phoneInput, code: phoneCode }),
      });
      const data = await res.json();
      if (data.success) {
        setShowPhoneModal(false);
        if (pendingAnswers !== null) {
          doRegister(pendingAnswers);
          setPendingAnswers(null);
        }
      } else {
        setPhoneError(data.detail || "绑定失败，请重试");
      }
    } catch {
      setPhoneError("网络错误");
    } finally {
      setPhoneLoading(false);
    }
  }

  function closePhoneModal() {
    setShowPhoneModal(false);
    setPhoneInput("");
    setPhoneCode("");
    setPhoneStep("input");
    setPhoneError("");
    setPendingAnswers(null);
  }

  return (
    <>
      <div className="flex flex-col gap-3">
        {/* 统计 + 立即报名（右上角主入口） */}
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">{statsText}</p>
          <div className="flex flex-col items-end gap-1">
            <Button onClick={handleClick} disabled={loading} size="lg" className="font-semibold">
              {loading ? "报名中..." : "立即报名"}
            </Button>
            {result && !result.success && (
              <p className="text-xs text-destructive">{result.message}</p>
            )}
          </div>
        </div>
        <ShareRow />
      </div>

      {showPhoneModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={closePhoneModal}
        >
          <div
            className="relative w-full max-w-sm bg-background rounded-xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-5 py-4 border-b">
              <h3 className="font-semibold">补充手机号</h3>
              <p className="text-xs text-muted-foreground mt-0.5">报名需要手机号以接收活动通知</p>
            </div>

            <div className="px-5 py-4 space-y-3">
              <div>
                <label className="text-sm font-medium">手机号</label>
                <Input
                  className="mt-1.5"
                  type="tel"
                  placeholder="请输入手机号"
                  value={phoneInput}
                  onChange={(e) => setPhoneInput(e.target.value)}
                  disabled={phoneStep === "verify"}
                />
              </div>

              {phoneStep === "verify" && (
                <div>
                  <label className="text-sm font-medium">验证码</label>
                  <div className="flex gap-2 mt-1.5">
                    <Input
                      placeholder="请输入验证码"
                      value={phoneCode}
                      onChange={(e) => setPhoneCode(e.target.value)}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      className="shrink-0"
                      onClick={sendPhoneCode}
                      disabled={countdown > 0 || phoneLoading}
                    >
                      {countdown > 0 ? `${countdown}s` : "重新发送"}
                    </Button>
                  </div>
                </div>
              )}

              {phoneError && <p className="text-xs text-destructive">{phoneError}</p>}
            </div>

            <div className="px-5 py-3 border-t flex gap-2">
              <Button variant="outline" className="flex-1" onClick={closePhoneModal}>
                取消
              </Button>
              {phoneStep === "input" ? (
                <Button className="flex-1" onClick={sendPhoneCode} disabled={phoneLoading}>
                  {phoneLoading ? "发送中..." : "获取验证码"}
                </Button>
              ) : (
                <Button className="flex-1" onClick={bindPhone} disabled={phoneLoading}>
                  {phoneLoading ? "绑定中..." : "确认绑定"}
                </Button>
              )}
            </div>
          </div>
        </div>
      )}

      {showForm && hasQuestions && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setShowForm(false)}
        >
          <div
            className="relative w-full max-w-md bg-background rounded-xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-5 py-4 border-b">
              <h3 className="font-semibold">报名信息</h3>
              <p className="text-xs text-muted-foreground mt-0.5">请填写以下信息完成报名</p>
            </div>

            <div className="px-5 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
              {questions!.map((q) => (
                <div key={q.id}>
                  <label className="text-sm font-medium">
                    {q.question_text}
                    {q.is_required && <span className="text-destructive ml-0.5">*</span>}
                  </label>

                  {q.question_type === "text" && (
                    <Input
                      className="mt-1.5"
                      placeholder="请输入..."
                      value={(answers[q.id] as string) || ""}
                      onChange={(e) => updateAnswer(q.id, e.target.value)}
                    />
                  )}

                  {q.question_type === "select" && q.options && (
                    <div className="mt-1.5 space-y-1.5">
                      {q.options.map((opt) => (
                        <label key={opt} className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="radio"
                            name={`q-${q.id}`}
                            checked={answers[q.id] === opt}
                            onChange={() => updateAnswer(q.id, opt)}
                            className="h-3.5 w-3.5"
                          />
                          <span className="text-sm">{opt}</span>
                        </label>
                      ))}
                    </div>
                  )}

                  {q.question_type === "multiselect" && q.options && (
                    <div className="mt-1.5 space-y-1.5">
                      {q.options.map((opt) => (
                        <label key={opt} className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={((answers[q.id] as string[]) || []).includes(opt)}
                            onChange={() => toggleMultiAnswer(q.id, opt)}
                            className="h-3.5 w-3.5 rounded border-input"
                          />
                          <span className="text-sm">{opt}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {formError && <p className="px-5 text-xs text-destructive">{formError}</p>}

            <div className="px-5 py-3 border-t flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setShowForm(false)}>
                取消
              </Button>
              <Button className="flex-1" onClick={validateAndSubmit} disabled={loading}>
                {loading ? "提交中..." : "提交报名"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

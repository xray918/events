"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRequireAuth } from "@/hooks/use-require-auth";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface UserProfile {
  id: string;
  nickname: string | null;
  avatar_url: string | null;
  phone: string | null;
  email: string | null;
}

interface Registration {
  id: string;
  event_id: string;
  event_title: string | null;
  event_slug: string | null;
  status: string;
  registered_via: string;
  qr_code_token: string;
  registered_at: string;
  checked_in_at: string | null;
}

interface MyEvent {
  id: string;
  title: string;
  slug: string;
  status: string;
  start_time: string;
  registration_count: number;
}

const statusMap: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  approved: { label: "已通过", variant: "default" },
  pending: { label: "待审批", variant: "secondary" },
  waitlisted: { label: "候补", variant: "outline" },
  declined: { label: "已拒绝", variant: "destructive" },
  cancelled: { label: "已取消", variant: "outline" },
};

export default function MyPage() {
  const { authenticated } = useRequireAuth();
  const [tab, setTab] = useState<"registrations" | "hosted">("registrations");
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [myEvents, setMyEvents] = useState<MyEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [editingNickname, setEditingNickname] = useState(false);
  const [nicknameInput, setNicknameInput] = useState("");
  const [nicknameSaving, setNicknameSaving] = useState(false);
  const [nicknameError, setNicknameError] = useState("");

  useEffect(() => {
    if (!authenticated) return;
    async function load() {
      try {
        const [regRes, evtRes, meRes] = await Promise.all([
          fetch(`${API}/api/v1/registrations/me`, { credentials: "include" }),
          fetch(`${API}/api/v1/events/mine`, { credentials: "include" }),
          fetch(`${API}/api/v1/auth/me`, { credentials: "include" }),
        ]);
        const regData = await regRes.json();
        const evtData = await evtRes.json();
        const meData = await meRes.json();
        if (regData.data) setRegistrations(regData.data);
        if (evtData.data) setMyEvents(evtData.data);
        if (meData.data) setProfile(meData.data);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [authenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  async function saveNickname() {
    if (!nicknameInput.trim()) {
      setNicknameError("昵称不能为空");
      return;
    }
    setNicknameSaving(true);
    setNicknameError("");
    try {
      const res = await fetch(`${API}/api/v1/auth/me`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ nickname: nicknameInput.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        setProfile((p) => p ? { ...p, nickname: data.data.nickname } : p);
        setEditingNickname(false);
      } else {
        setNicknameError(data.detail || "保存失败");
      }
    } catch {
      setNicknameError("网络错误");
    } finally {
      setNicknameSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <p className="text-muted-foreground">加载中...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-3xl font-bold tracking-tight">我的活动</h1>

      {/* 个人资料 */}
      {profile && (
        <div className="mt-4 rounded-xl border bg-card p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {profile.avatar_url ? (
              <img src={profile.avatar_url} alt="" className="h-10 w-10 rounded-full" />
            ) : (
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-sm font-medium">
                {(profile.nickname || "?")[0]}
              </span>
            )}
            <div>
              {editingNickname ? (
                <div className="flex items-center gap-2">
                  <Input
                    value={nicknameInput}
                    onChange={(e) => setNicknameInput(e.target.value)}
                    className="h-7 w-40 text-sm"
                    autoFocus
                    onKeyDown={(e) => { if (e.key === "Enter") saveNickname(); if (e.key === "Escape") setEditingNickname(false); }}
                  />
                  <Button size="sm" onClick={saveNickname} disabled={nicknameSaving} className="h-7 px-2 text-xs">
                    {nicknameSaving ? "保存中…" : "保存"}
                  </Button>
                  <button onClick={() => setEditingNickname(false)} className="text-xs text-muted-foreground hover:text-foreground">取消</button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{profile.nickname || "未设置昵称"}</span>
                  <button
                    onClick={() => { setNicknameInput(profile.nickname || ""); setEditingNickname(true); setNicknameError(""); }}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    修改
                  </button>
                </div>
              )}
              {nicknameError && <p className="text-xs text-destructive mt-0.5">{nicknameError}</p>}
              <p className="text-xs text-muted-foreground mt-0.5">
                {profile.phone || profile.email || ""}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 flex gap-3">
        <button
          onClick={() => setTab("registrations")}
          className={`rounded-full px-5 py-2 text-sm font-medium transition-colors ${
            tab === "registrations"
              ? "bg-foreground text-background"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          我的报名
        </button>
        <button
          onClick={() => setTab("hosted")}
          className={`rounded-full px-5 py-2 text-sm font-medium transition-colors ${
            tab === "hosted"
              ? "bg-foreground text-background"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          我创建的
        </button>
      </div>

      <div className="mt-4 space-y-3">
        {tab === "registrations" && (
          <>
            {registrations.length === 0 ? (
              <div className="rounded-xl border border-dashed py-12 text-center">
                <p className="text-muted-foreground">还没有报名任何活动</p>
                <Link href="/">
                  <Button variant="outline" className="mt-3">浏览活动</Button>
                </Link>
              </div>
            ) : (
              registrations.map((reg) => {
                const s = statusMap[reg.status] || { label: reg.status, variant: "outline" as const };
                return (
                  <Link key={reg.id} href={reg.event_slug ? `/e/${reg.event_slug}` : "#"}>
                    <Card className="hover:shadow-md transition-shadow cursor-pointer">
                      <CardContent className="flex items-center justify-between p-4">
                        <div>
                          <p className="font-medium">{reg.event_title || "活动"}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {new Date(reg.registered_at).toLocaleDateString("zh-CN")} 报名
                            {reg.registered_via === "agent_api" && " · Agent 代报名"}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={s.variant}>{s.label}</Badge>
                          {reg.status === "approved" && !reg.checked_in_at && (
                            <Link href={`/checkin/${reg.qr_code_token}`}>
                              <Button variant="outline" size="sm">签到码</Button>
                            </Link>
                          )}
                          {reg.checked_in_at && (
                            <Badge variant="default">已签到</Badge>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })
            )}
          </>
        )}

        {tab === "hosted" && (
          <>
            {myEvents.length === 0 ? (
              <div className="rounded-xl border border-dashed py-12 text-center">
                <p className="text-muted-foreground">还没有创建活动</p>
                <Link href="/create">
                  <Button variant="outline" className="mt-3">创建活动</Button>
                </Link>
              </div>
            ) : (
              myEvents.map((evt) => {
                const statusInfo: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
                  published: { label: "已发布", variant: "default" },
                  draft: { label: "草稿", variant: "secondary" },
                  cancelled: { label: "已取消", variant: "destructive" },
                  completed: { label: "已结束", variant: "outline" },
                };
                const si = statusInfo[evt.status] || { label: evt.status, variant: "outline" as const };
                return (
                  <Link key={evt.id} href={evt.status === "draft" ? `/edit/${evt.id}` : `/manage/${evt.id}`}>
                    <Card className="hover:shadow-md transition-shadow cursor-pointer">
                      <CardContent className="flex items-center justify-between p-4">
                        <div>
                          <p className="font-medium">{evt.title}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {new Date(evt.start_time).toLocaleDateString("zh-CN")}
                            {evt.registration_count > 0 && ` · ${evt.registration_count} 人报名`}
                          </p>
                        </div>
                        <Badge variant={si.variant}>{si.label}</Badge>
                      </CardContent>
                    </Card>
                  </Link>
                );
              })
            )}
          </>
        )}
      </div>
    </div>
  );
}

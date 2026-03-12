"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRequireAuth } from "@/hooks/use-require-auth";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

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
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [myEvents, setMyEvents] = useState<MyEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authenticated) return;
    async function load() {
      try {
        const [regRes, evtRes] = await Promise.all([
          fetch(`${API}/api/v1/registrations/me`, { credentials: "include" }),
          fetch(`${API}/api/v1/events?status=draft`, { credentials: "include" }),
        ]);
        const regData = await regRes.json();
        const evtData = await evtRes.json();
        if (regData.data) setRegistrations(regData.data);
        if (evtData.data) setMyEvents(evtData.data);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [authenticated]); // eslint-disable-line react-hooks/exhaustive-deps

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

      <Tabs defaultValue="registrations" className="mt-6">
        <TabsList>
          <TabsTrigger value="registrations">我的报名</TabsTrigger>
          <TabsTrigger value="hosted">我创建的</TabsTrigger>
        </TabsList>

        <TabsContent value="registrations" className="mt-4 space-y-3">
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
        </TabsContent>

        <TabsContent value="hosted" className="mt-4 space-y-3">
          {myEvents.length === 0 ? (
            <div className="rounded-xl border border-dashed py-12 text-center">
              <p className="text-muted-foreground">还没有创建活动</p>
              <Link href="/create">
                <Button variant="outline" className="mt-3">创建活动</Button>
              </Link>
            </div>
          ) : (
            myEvents.map((evt) => (
              <Link key={evt.id} href={`/manage/${evt.id}`}>
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardContent className="flex items-center justify-between p-4">
                    <div>
                      <p className="font-medium">{evt.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {new Date(evt.start_time).toLocaleDateString("zh-CN")}
                      </p>
                    </div>
                    <Badge variant={evt.status === "published" ? "default" : "secondary"}>
                      {evt.status === "published" ? "已发布" : evt.status === "draft" ? "草稿" : evt.status}
                    </Badge>
                  </CardContent>
                </Card>
              </Link>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

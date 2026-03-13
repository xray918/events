"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface CheckinInfo {
  registration_id: string;
  event_title: string | null;
  user_nickname: string | null;
  status: string;
  already_checked_in: boolean;
  checked_in_at: string | null;
}

export default function CheckinPage() {
  const params = useParams();
  const token = params.token as string;
  const [info, setInfo] = useState<CheckinInfo | null>(null);
  const [qrUrl, setQrUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [selfCheckinLoading, setSelfCheckinLoading] = useState(false);
  const [selfCheckinDone, setSelfCheckinDone] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API}/api/v1/checkin/verify/${token}`);
        const data = await res.json();
        if (data.success) {
          setInfo(data.data);
          setQrUrl(`${API}/api/v1/checkin/qr/${token}`);
        } else {
          setError(data.detail || "无效的签到码");
        }
      } catch {
        setError("网络错误");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [token]);

  async function handleSelfCheckin() {
    setSelfCheckinLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/checkin/self/${token}`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.success) {
        setSelfCheckinDone(true);
        if (info) {
          setInfo({ ...info, already_checked_in: true, checked_in_at: new Date().toISOString() });
        }
      } else {
        setError(data.detail || "签到失败");
      }
    } catch {
      setError("网络错误");
    } finally {
      setSelfCheckinLoading(false);
    }
  }

  if (loading) {
    return <div className="mx-auto max-w-md px-4 py-20 text-center"><p className="text-muted-foreground">加载中...</p></div>;
  }

  if (error && !info) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  if (!info) return null;

  return (
    <div className="mx-auto max-w-md px-4 py-10">
      <Card>
        <CardContent className="p-6 text-center space-y-4">
          <h1 className="text-xl font-bold">{info.event_title || "活动签到"}</h1>

          {info.already_checked_in || selfCheckinDone ? (
            <div className="space-y-2">
              <Badge variant="default" className="text-base px-4 py-1">已签到</Badge>
              <p className="text-sm text-muted-foreground">
                签到时间: {info.checked_in_at ? new Date(info.checked_in_at).toLocaleString("zh-CN") : "刚刚"}
              </p>
            </div>
          ) : info.status === "approved" ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">请出示此二维码给工作人员扫描，或自助签到</p>
              {qrUrl && (
                <div className="flex justify-center">
                  <img
                    src={qrUrl}
                    alt="签到二维码"
                    className="h-48 w-48 rounded-lg"
                  />
                </div>
              )}
              <div className="rounded-lg bg-muted p-3">
                <p className="text-xs text-muted-foreground">参会者</p>
                <p className="font-medium">{info.user_nickname || "—"}</p>
              </div>
              <Button
                onClick={handleSelfCheckin}
                disabled={selfCheckinLoading}
                className="w-full"
                size="lg"
              >
                {selfCheckinLoading ? "签到中..." : "自助签到"}
              </Button>
              {error && <p className="text-xs text-destructive">{error}</p>}
            </div>
          ) : (
            <div className="space-y-2">
              <Badge variant="secondary">
                {info.status === "pending" ? "待审批" : info.status === "waitlisted" ? "候补中" : info.status}
              </Badge>
              <p className="text-sm text-muted-foreground">报名尚未通过审批，暂时无法签到。</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

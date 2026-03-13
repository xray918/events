"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface Props {
  eventId: string;
  eventStatus: string;
  hostId: string;
  circleId?: string | null;
}

export function HostActions({ eventId, eventStatus, hostId, circleId: initialCircleId }: Props) {
  const router = useRouter();
  const [isHost, setIsHost] = useState(false);
  const [loading, setLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [status, setStatus] = useState(eventStatus);
  const [syncToClawdchat, setSyncToClawdchat] = useState(true);
  const [circleId, setCircleId] = useState(initialCircleId);

  useEffect(() => {
    fetch(`${API}/api/v1/auth/me`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        const userId = data.data?.id;
        if (userId === hostId) setIsHost(true);
      })
      .catch(() => {});
  }, [hostId]);

  if (!isHost) return null;

  async function handlePublish() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/events/${eventId}/publish`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sync_to_clawdchat: syncToClawdchat }),
      });
      const data = await res.json();
      if (data.success) {
        setStatus("published");
        if (data.data?.circle_id) setCircleId(data.data.circle_id);
        router.refresh();
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSyncClawdchat() {
    setSyncLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/events/${eventId}/sync-clawdchat`, {
        method: "POST",
        credentials: "include",
      });
      const data = await res.json();
      if (data.success && data.data?.circle_id) {
        setCircleId(data.data.circle_id);
        router.refresh();
      }
    } finally {
      setSyncLoading(false);
    }
  }

  return (
    <div className="rounded-xl border-2 border-dashed border-primary/30 bg-primary/5 p-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">主办方操作</span>
          <Badge variant={status === "draft" ? "secondary" : status === "published" ? "default" : "outline"}>
            {{ draft: "草稿", published: "已发布", cancelled: "已取消", completed: "已结束" }[status] || status}
          </Badge>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {status === "draft" && (
            <>
              <label className="flex items-center gap-1.5 text-sm cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={syncToClawdchat}
                  onChange={(e) => setSyncToClawdchat(e.target.checked)}
                  className="rounded border-gray-300"
                />
                同步到虾聊
              </label>
              <Button size="sm" onClick={handlePublish} disabled={loading}>
                {loading ? "发布中..." : "发布活动"}
              </Button>
            </>
          )}
          {status === "published" && !circleId && (
            <Button size="sm" variant="outline" onClick={handleSyncClawdchat} disabled={syncLoading}>
              {syncLoading ? "同步中..." : "同步到虾聊"}
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => router.push(`/manage/${eventId}`)}>
            报名管理
          </Button>
          <Button size="sm" variant="outline" onClick={() => router.push(`/edit/${eventId}`)}>
            编辑活动
          </Button>
        </div>
      </div>
    </div>
  );
}

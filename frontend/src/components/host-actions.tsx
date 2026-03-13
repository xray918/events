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
}

export function HostActions({ eventId, eventStatus, hostId }: Props) {
  const router = useRouter();
  const [isHost, setIsHost] = useState(false);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(eventStatus);

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
      });
      const data = await res.json();
      if (data.success) {
        setStatus("published");
        router.refresh();
      }
    } finally {
      setLoading(false);
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
            <Button size="sm" onClick={handlePublish} disabled={loading}>
              {loading ? "发布中..." : "发布活动"}
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

"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface SharePosterButtonProps {
  slug: string;
  title: string;
}

export function SharePosterButton({ slug, title }: SharePosterButtonProps) {
  const [showPoster, setShowPoster] = useState(false);
  const [copied, setCopied] = useState(false);
  const [posterKey] = useState(() => Date.now());
  const posterUrl = `${API}/api/v1/events/${slug}/poster?v=${posterKey}`;
  const eventUrl = `${typeof window !== "undefined" ? window.location.origin : ""}/e/${slug}`;

  async function handleShareLink() {
    if (navigator.share) {
      try {
        await navigator.share({ title, text: `邀请你参加活动「${title}」`, url: eventUrl });
        return;
      } catch {
        /* user cancelled or not supported */
      }
    }
    try {
      await navigator.clipboard.writeText(eventUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  }

  return (
    <>
      {/* 分享链接 */}
      <Button
        variant="outline"
        size="sm"
        onClick={handleShareLink}
      >
        {copied ? "✓ 已复制" : "分享链接"}
      </Button>

      {/* 分享海报 */}
      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowPoster(true)}
      >
        分享海报
      </Button>

      {/* 海报弹窗 */}
      {showPoster && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setShowPoster(false)}
        >
          <div
            className="relative max-h-[90vh] max-w-[400px] w-full bg-white rounded-xl overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 text-center border-b">
              <p className="font-medium text-sm text-gray-800">长按保存图片，微信扫码报名</p>
            </div>
            <div className="overflow-y-auto" style={{ maxHeight: "75vh" }}>
              <img
                src={posterUrl}
                alt={`${title} 活动海报`}
                className="w-full"
                loading="eager"
              />
            </div>
            <div className="p-3 flex gap-2 border-t">
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => setShowPoster(false)}
              >
                关闭
              </Button>
              <Button
                size="sm"
                className="flex-1"
                onClick={() => {
                  const a = document.createElement("a");
                  a.href = posterUrl;
                  a.download = `${title}-海报.png`;
                  a.click();
                }}
              >
                下载海报
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

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
  const posterUrl = `${API}/api/v1/events/${slug}/poster`;

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowPoster(true)}
      >
        分享
      </Button>

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
            <div className="flex justify-center p-2">
              <img
                src={posterUrl}
                alt={`${title} 活动海报`}
                className="max-h-[70vh] w-auto"
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

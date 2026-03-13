"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface FeedbackItem {
  id: string;
  rating: number;
  comment: string | null;
  user: { nickname: string | null; avatar_url: string | null };
  created_at: string | null;
}

export function EventFeedback({ slug }: { slug: string }) {
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [avgRating, setAvgRating] = useState(0);
  const [count, setCount] = useState(0);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [hoverRating, setHoverRating] = useState(0);

  useEffect(() => {
    fetch(`${API}/api/v1/events/${slug}/feedback`)
      .then((r) => r.json())
      .then((data) => {
        if (data.success && data.data) {
          setFeedbacks(data.data.items || []);
          setAvgRating(data.data.avg_rating || 0);
          setCount(data.data.count || 0);
        }
      })
      .catch(() => {});
  }, [slug, submitted]);

  async function handleSubmit() {
    if (!rating) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/api/v1/events/${slug}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ rating, comment: comment.trim() || null }),
      });
      const data = await res.json();
      if (data.success) {
        setSubmitted(true);
      }
    } finally {
      setSubmitting(false);
    }
  }

  const stars = [1, 2, 3, 4, 5];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">活动评价</h2>
        {count > 0 && (
          <span className="text-sm text-muted-foreground">
            {avgRating} 分 · {count} 条评价
          </span>
        )}
      </div>

      {!submitted && (
        <Card>
          <CardContent className="p-4 space-y-3">
            <p className="text-sm font-medium">你的评价</p>
            <div className="flex gap-1">
              {stars.map((s) => (
                <button
                  key={s}
                  onMouseEnter={() => setHoverRating(s)}
                  onMouseLeave={() => setHoverRating(0)}
                  onClick={() => setRating(s)}
                  className="text-2xl transition-colors"
                >
                  {s <= (hoverRating || rating) ? "★" : "☆"}
                </button>
              ))}
            </div>
            <textarea
              placeholder="分享你的参会感受（可选）"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            />
            <Button size="sm" onClick={handleSubmit} disabled={!rating || submitting}>
              {submitting ? "提交中..." : "提交评价"}
            </Button>
          </CardContent>
        </Card>
      )}

      {submitted && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-green-600">感谢你的评价！</p>
          </CardContent>
        </Card>
      )}

      {feedbacks.length > 0 && (
        <div className="space-y-3">
          {feedbacks.map((fb) => (
            <div key={fb.id} className="flex gap-3 rounded-lg bg-muted/50 p-3">
              <div className="flex-shrink-0">
                {fb.user?.avatar_url ? (
                  <img src={fb.user.avatar_url} alt="" className="h-8 w-8 rounded-full" />
                ) : (
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs">
                    {(fb.user?.nickname || "?")[0]}
                  </span>
                )}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{fb.user?.nickname}</span>
                  <span className="text-xs text-amber-500">
                    {"★".repeat(fb.rating)}{"☆".repeat(5 - fb.rating)}
                  </span>
                </div>
                {fb.comment && <p className="mt-1 text-sm text-muted-foreground">{fb.comment}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

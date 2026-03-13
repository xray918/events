"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { QrScanner } from "@/components/qr-scanner";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

export default function StaffCheckinPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const eventId = params.id as string;
  const checkinKey = searchParams.get("key") || "";

  const [eventTitle, setEventTitle] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanResult, setScanResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [checkinCount, setCheckinCount] = useState(0);

  const lastScannedRef = useRef("");
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (!checkinKey) {
      setError("缺少签到密钥");
      setLoading(false);
      return;
    }
    fetch(`${API}/api/v1/events/${eventId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.success && data.data) {
          setEventTitle(data.data.title);
        } else {
          setError("活动不存在");
        }
      })
      .catch(() => setError("网络错误"))
      .finally(() => setLoading(false));
  }, [eventId, checkinKey]);

  async function handleScan(qrToken: string) {
    const t = qrToken.trim();
    if (!t || t === lastScannedRef.current) return;
    lastScannedRef.current = t;
    setScanLoading(true);
    setScanResult(null);

    try {
      const res = await fetch(`${API}/api/v1/checkin/scan-by-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ qr_token: t, checkin_key: checkinKey }),
      });
      const data = await res.json();
      if (data.success) {
        setScanResult({ ok: true, message: data.data.message });
        if (!data.data.already_checked_in) {
          setCheckinCount((c) => c + 1);
        }
      } else {
        setScanResult({ ok: false, message: data.detail || "签到失败" });
      }
    } catch {
      setScanResult({ ok: false, message: "网络错误" });
    } finally {
      setScanLoading(false);
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        lastScannedRef.current = "";
        setScanResult(null);
      }, 3000);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <p className="text-muted-foreground">加载中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <p className="text-destructive text-lg font-medium">{error}</p>
        <p className="text-sm text-muted-foreground mt-2">请联系活动主办方获取正确的签到链接</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md px-4 py-6">
      <div className="text-center mb-6">
        <h1 className="text-xl font-bold">{eventTitle}</h1>
        <p className="text-sm text-muted-foreground mt-1">工作人员签到</p>
        {checkinCount > 0 && (
          <p className="text-xs text-green-600 mt-1">
            本次已签到 {checkinCount} 人
          </p>
        )}
      </div>

      <Card>
        <CardContent className="p-4 space-y-3">
          <QrScanner onScan={handleScan} paused={scanLoading} />

          {scanResult && (
            <div
              className={`rounded-lg p-4 text-center font-medium ${
                scanResult.ok
                  ? "bg-green-50 text-green-700 text-lg"
                  : "bg-red-50 text-destructive text-sm"
              }`}
            >
              {scanResult.message}
            </div>
          )}
        </CardContent>
      </Card>

      <p className="text-center text-xs text-muted-foreground mt-6">
        扫描参会者手机上的签到二维码即可完成签到
      </p>
    </div>
  );
}

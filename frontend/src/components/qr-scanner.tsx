"use client";

import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { Button } from "@/components/ui/button";

interface QrScannerProps {
  /** Called with the decoded text when a QR code is scanned */
  onScan: (decodedText: string) => void;
  /** Whether to pause scanning (e.g. while processing a result) */
  paused?: boolean;
}

export function QrScanner({ onScan, paused }: QrScannerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const onScanRef = useRef(onScan);
  onScanRef.current = onScan;

  useEffect(() => {
    return () => {
      scannerRef.current?.stop().catch(() => {});
      scannerRef.current?.clear();
      scannerRef.current = null;
    };
  }, []);

  async function start() {
    setError("");
    if (!containerRef.current) return;

    const elementId = containerRef.current.id;
    const scanner = new Html5Qrcode(elementId);
    scannerRef.current = scanner;

    try {
      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
          onScanRef.current(decodedText);
        },
        () => {},
      );
      setRunning(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("Permission") || msg.includes("NotAllowed")) {
        setError("请允许使用摄像头权限");
      } else if (msg.includes("NotFound") || msg.includes("device")) {
        setError("未检测到摄像头");
      } else {
        setError(`无法启动摄像头: ${msg}`);
      }
    }
  }

  async function stop() {
    try {
      await scannerRef.current?.stop();
    } catch { /* ignore */ }
    scannerRef.current?.clear();
    scannerRef.current = null;
    setRunning(false);
  }

  useEffect(() => {
    if (paused && running) {
      scannerRef.current?.pause(true);
    } else if (!paused && running) {
      try { scannerRef.current?.resume(); } catch { /* ignore */ }
    }
  }, [paused, running]);

  return (
    <div className="space-y-3">
      <div
        id="qr-scanner-region"
        ref={containerRef}
        className="overflow-hidden rounded-lg bg-black"
        style={{ minHeight: running ? 300 : 0 }}
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button
        type="button"
        variant={running ? "outline" : "default"}
        className="w-full"
        onClick={running ? stop : start}
      >
        {running ? "关闭摄像头" : "📷 打开摄像头扫码"}
      </Button>
    </div>
  );
}

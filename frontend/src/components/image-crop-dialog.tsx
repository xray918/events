"use client";

import { useState, useCallback } from "react";
import Cropper, { Area } from "react-easy-crop";

interface ImageCropDialogProps {
  imageSrc: string;
  onConfirm: (croppedBlob: Blob) => void;
  onCancel: () => void;
  aspect?: number;
}

async function getCroppedBlob(
  imageSrc: string,
  pixelCrop: Area,
): Promise<Blob> {
  const image = new Image();
  image.crossOrigin = "anonymous";
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = reject;
    image.src = imageSrc;
  });

  const canvas = document.createElement("canvas");
  canvas.width = pixelCrop.width;
  canvas.height = pixelCrop.height;
  const ctx = canvas.getContext("2d")!;

  ctx.drawImage(
    image,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    pixelCrop.width,
    pixelCrop.height,
  );

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Canvas toBlob failed"))),
      "image/jpeg",
      0.92,
    );
  });
}

export function ImageCropDialog({
  imageSrc,
  onConfirm,
  onCancel,
  aspect = 16 / 9,
}: ImageCropDialogProps) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [processing, setProcessing] = useState(false);

  const onCropComplete = useCallback((_: Area, areaPixels: Area) => {
    setCroppedAreaPixels(areaPixels);
  }, []);

  async function handleConfirm() {
    if (!croppedAreaPixels) return;
    setProcessing(true);
    try {
      const blob = await getCroppedBlob(imageSrc, croppedAreaPixels);
      onConfirm(blob);
    } catch {
      onCancel();
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="relative w-full max-w-xl bg-background rounded-xl shadow-2xl overflow-hidden">
        <div className="px-4 py-3 border-b text-center">
          <p className="font-medium text-sm">调整封面图片</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            拖拽移动 · 滚轮缩放 · 双指缩放
          </p>
        </div>

        <div className="relative w-full" style={{ height: "360px" }}>
          <Cropper
            image={imageSrc}
            crop={crop}
            zoom={zoom}
            aspect={aspect}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={onCropComplete}
            minZoom={0.5}
            maxZoom={5}
            objectFit="contain"
          />
        </div>

        <div className="px-6 py-3 border-t">
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground shrink-0">缩小</span>
            <input
              type="range"
              min={0.5}
              max={5}
              step={0.01}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="flex-1 h-1.5 accent-primary cursor-pointer"
            />
            <span className="text-xs text-muted-foreground shrink-0">放大</span>
          </div>
        </div>

        <div className="flex gap-3 p-4 border-t">
          <button
            type="button"
            onClick={onCancel}
            disabled={processing}
            className="flex-1 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={processing}
            className="flex-1 rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {processing ? "处理中..." : "确认裁剪"}
          </button>
        </div>
      </div>
    </div>
  );
}

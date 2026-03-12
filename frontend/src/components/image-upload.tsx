"use client";

import { useState, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface ImageUploadProps {
  value: string;
  onChange: (url: string) => void;
  className?: string;
}

export function ImageUpload({ value, onChange, className }: ImageUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (!file.type.startsWith("image/")) {
      setError("请选择图片文件");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("图片不能超过 5MB");
      return;
    }

    setUploading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/api/v1/upload/image`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        onChange(data.url);
      } else {
        setError(data.detail || "上传失败");
      }
    } catch {
      setError("上传失败，请重试");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className={className}>
      <label className="text-sm font-medium">活动封面</label>
      <div
        className="mt-1.5 relative flex items-center justify-center rounded-xl border-2 border-dashed cursor-pointer overflow-hidden transition-colors hover:border-primary/50"
        style={{ height: 200 }}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          const file = e.dataTransfer.files[0];
          if (file) handleFile(file);
        }}
      >
        {value ? (
          <>
            <img
              src={value}
              alt="封面预览"
              className="absolute inset-0 h-full w-full object-cover"
            />
            <div className="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
              <span className="text-white text-sm font-medium">点击更换封面</span>
            </div>
          </>
        ) : (
          <div className="text-center text-muted-foreground">
            {uploading ? (
              <p className="text-sm">上传中...</p>
            ) : (
              <>
                <p className="text-2xl mb-1">🖼️</p>
                <p className="text-sm">点击或拖拽上传封面图</p>
                <p className="text-xs mt-1">支持 jpg/png/webp，最大 5MB</p>
              </>
            )}
          </div>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}

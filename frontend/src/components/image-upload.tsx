"use client";

import { useState, useRef, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface ImageUploadProps {
  value: string;
  onChange: (url: string) => void;
  className?: string;
  /** When a theme is selected, pass its CSS style to render as cover preview */
  themeStyle?: React.CSSProperties;
}

export function ImageUpload({ value, onChange, className, themeStyle }: ImageUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [localPreview, setLocalPreview] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!value) setLocalPreview("");
  }, [value]);

  useEffect(() => {
    return () => {
      if (localPreview) URL.revokeObjectURL(localPreview);
    };
  }, [localPreview]);

  async function handleFile(file: File) {
    if (!file.type.startsWith("image/")) {
      setError("请选择图片文件");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("图片不能超过 5MB");
      return;
    }

    setLocalPreview(URL.createObjectURL(file));
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
        setLocalPreview("");
      }
    } catch {
      setError("上传失败，请重试");
      setLocalPreview("");
    } finally {
      setUploading(false);
    }
  }

  const previewSrc = localPreview || value;
  const hasThemeBg = !previewSrc && !!themeStyle;

  return (
    <div className={className}>
      <label className="text-sm font-medium">活动封面</label>
      <div
        className={`mt-1.5 relative flex items-center justify-center rounded-xl border-2 border-dashed cursor-pointer overflow-hidden transition-colors hover:border-primary/50`}
        style={{ height: 200, ...(hasThemeBg ? themeStyle : {}) }}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          const file = e.dataTransfer.files[0];
          if (file) handleFile(file);
        }}
      >
        {previewSrc ? (
          <>
            <img
              src={previewSrc}
              alt="封面预览"
              className="absolute inset-0 h-full w-full object-cover"
              onError={() => {
                if (!localPreview && value) setError("图片加载失败，请重新上传");
              }}
            />
            {uploading && (
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                <span className="text-white text-sm font-medium">上传中...</span>
              </div>
            )}
            <div className="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
              <span className="text-white text-sm font-medium">点击更换封面</span>
            </div>
          </>
        ) : hasThemeBg ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="opacity-0 hover:opacity-100 transition-opacity absolute inset-0 bg-black/20 flex items-center justify-center">
              <span className="text-white text-sm font-medium">点击上传自定义封面</span>
            </div>
          </div>
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

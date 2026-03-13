"use client";

import { useState, useRef, useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface DescriptionEditorProps {
  value: string;
  onChange: (value: string) => void;
  onAIGenerate?: () => void;
  aiLoading?: boolean;
  placeholder?: string;
  rows?: number;
}

export function DescriptionEditor({
  value,
  onChange,
  onAIGenerate,
  aiLoading,
  placeholder = "详细介绍你的活动...（支持 Markdown 格式）",
  rows = 8,
}: DescriptionEditorProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const insertAtCursor = useCallback(
    (text: string) => {
      const el = textareaRef.current;
      if (!el) {
        onChange(value + text);
        return;
      }
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const before = value.slice(0, start);
      const after = value.slice(end);
      const needNewlineBefore = before.length > 0 && !before.endsWith("\n");
      const needNewlineAfter = after.length > 0 && !after.startsWith("\n");
      const inserted = `${needNewlineBefore ? "\n" : ""}${text}${needNewlineAfter ? "\n" : ""}`;
      const newValue = before + inserted + after;
      onChange(newValue);

      requestAnimationFrame(() => {
        const pos = before.length + inserted.length;
        el.selectionStart = pos;
        el.selectionEnd = pos;
        el.focus();
      });
    },
    [value, onChange],
  );

  const uploadAndInsert = useCallback(
    async (file: File) => {
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
        if (data.success && data.url) {
          const name = file.name.replace(/\.[^.]+$/, "") || "image";
          insertAtCursor(`![${name}](${data.url})`);
        } else {
          setError(data.detail || "图片上传失败");
        }
      } catch {
        setError("图片上传失败，请重试");
      } finally {
        setUploading(false);
      }
    },
    [insertAtCursor],
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          e.preventDefault();
          const file = item.getAsFile();
          if (file) uploadAndInsert(file);
          return;
        }
      }
    },
    [uploadAndInsert],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLTextAreaElement>) => {
      const file = e.dataTransfer?.files?.[0];
      if (file?.type.startsWith("image/")) {
        e.preventDefault();
        e.stopPropagation();
        uploadAndInsert(file);
      }
    },
    [uploadAndInsert],
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent<HTMLTextAreaElement>) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        e.preventDefault();
        e.stopPropagation();
      }
    },
    [],
  );

  return (
    <div>
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">活动描述</label>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="text-xs"
          >
            {uploading ? "上传中..." : "🖼️ 插入图片"}
          </Button>
          {onAIGenerate && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onAIGenerate}
              disabled={aiLoading}
              className="text-xs"
            >
              {aiLoading ? "AI 生成中..." : "✨ AI 生成"}
            </Button>
          )}
        </div>
      </div>

      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onPaste={handlePaste}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        placeholder={placeholder}
        rows={rows}
        className="mt-1.5 font-mono text-sm"
      />

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) uploadAndInsert(file);
          e.target.value = "";
        }}
      />

      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}

      <p className="mt-1 text-xs text-muted-foreground">
        支持 Markdown：**加粗**、- 列表、![图片](url)。可直接粘贴或拖拽图片到编辑区。
      </p>
    </div>
  );
}

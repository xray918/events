"use client";

import { useState, useRef, useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { EventDescription } from "@/components/event-description";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface DescriptionEditorProps {
  value: string;
  onChange: (value: string) => void;
  onAIGenerate?: (extraPrompt?: string) => void;
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
  const [tab, setTab] = useState<"edit" | "preview">("edit");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [aiDialogOpen, setAiDialogOpen] = useState(false);
  const [aiExtraPrompt, setAiExtraPrompt] = useState("");
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
      {/* 标题行：左侧 Tab 切换，右侧工具按钮 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-0.5">
          <label className="text-sm font-medium mr-3">活动描述</label>
          <button
            type="button"
            onClick={() => setTab("edit")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              tab === "edit"
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            编辑
          </button>
          <button
            type="button"
            onClick={() => setTab("preview")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              tab === "preview"
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            预览
          </button>
        </div>

        {tab === "edit" && (
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
                onClick={() => setAiDialogOpen(true)}
                disabled={aiLoading}
                className="text-xs"
              >
                {aiLoading ? "AI 生成中..." : "✨ AI 生成"}
              </Button>
            )}
          </div>
        )}
      </div>

      {/* 编辑区 */}
      {tab === "edit" && (
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
      )}

      {/* 预览区 */}
      {tab === "preview" && (
        <div className="mt-1.5 min-h-32 rounded-lg border border-input bg-muted/30 px-3 py-2.5">
          {value.trim() ? (
            <EventDescription content={value} />
          ) : (
            <p className="text-sm text-muted-foreground">暂无内容，请先在编辑模式下输入描述。</p>
          )}
        </div>
      )}

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

      {tab === "edit" && (
        <p className="mt-1 text-xs text-muted-foreground">
          支持 Markdown：**加粗**、- 列表、![图片](url)。可直接粘贴或拖拽图片到编辑区。
        </p>
      )}

      {/* AI 生成弹窗 */}
      {onAIGenerate && (
        <Dialog open={aiDialogOpen} onOpenChange={setAiDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>✨ AI 生成活动描述</DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <p className="text-sm text-muted-foreground">
                AI 将根据活动名称、类型、地点等信息自动生成描述。你也可以在下方补充额外要求。
              </p>
              <Textarea
                value={aiExtraPrompt}
                onChange={(e) => setAiExtraPrompt(e.target.value)}
                placeholder="可选：补充描述风格或特别说明，如「语气活泼」「强调技术深度」「面向初学者」……"
                rows={4}
                className="text-sm"
              />
            </div>
            <DialogFooter className="gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => { setAiDialogOpen(false); setAiExtraPrompt(""); }}
              >
                取消
              </Button>
              <Button
                type="button"
                disabled={aiLoading}
                onClick={() => {
                  setAiDialogOpen(false);
                  onAIGenerate(aiExtraPrompt.trim() || undefined);
                  setAiExtraPrompt("");
                }}
              >
                {aiLoading ? "生成中..." : "开始生成"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

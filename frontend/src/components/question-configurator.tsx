"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface QuestionDraft {
  question_text: string;
  question_type: "text" | "select" | "multiselect";
  options: string[];
  is_required: boolean;
}

const PRESET_QUESTIONS: QuestionDraft[] = [
  { question_text: "你的公司/组织？", question_type: "text", options: [], is_required: false },
  { question_text: "你的职位/角色？", question_type: "text", options: [], is_required: false },
  {
    question_text: "你是如何了解到本活动的？",
    question_type: "select",
    options: ["朋友推荐", "社交媒体", "搜索引擎", "社区/论坛", "其他"],
    is_required: false,
  },
  { question_text: "有什么想对主办方说的？", question_type: "text", options: [], is_required: false },
];

interface Props {
  value: QuestionDraft[];
  onChange: (questions: QuestionDraft[]) => void;
}

export function QuestionConfigurator({ value, onChange }: Props) {
  const [showPresets, setShowPresets] = useState(false);

  function addQuestion() {
    onChange([...value, { question_text: "", question_type: "text", options: [], is_required: false }]);
  }

  function removeQuestion(idx: number) {
    onChange(value.filter((_, i) => i !== idx));
  }

  function updateQuestion(idx: number, field: keyof QuestionDraft, val: unknown) {
    const updated = [...value];
    updated[idx] = { ...updated[idx], [field]: val };
    if (field === "question_type" && val === "text") {
      updated[idx].options = [];
    }
    onChange(updated);
  }

  function addOption(qIdx: number) {
    const updated = [...value];
    updated[qIdx] = { ...updated[qIdx], options: [...updated[qIdx].options, ""] };
    onChange(updated);
  }

  function addOtherOption(qIdx: number) {
    const updated = [...value];
    const opts = updated[qIdx].options;
    if (!opts.includes("其他（请说明）")) {
      updated[qIdx] = { ...updated[qIdx], options: [...opts, "其他（请说明）"] };
      onChange(updated);
    }
  }

  function updateOption(qIdx: number, optIdx: number, val: string) {
    const updated = [...value];
    const opts = [...updated[qIdx].options];
    opts[optIdx] = val;
    updated[qIdx] = { ...updated[qIdx], options: opts };
    onChange(updated);
  }

  function removeOption(qIdx: number, optIdx: number) {
    const updated = [...value];
    updated[qIdx] = { ...updated[qIdx], options: updated[qIdx].options.filter((_, i) => i !== optIdx) };
    onChange(updated);
  }

  function addPreset(preset: QuestionDraft) {
    onChange([...value, { ...preset }]);
    setShowPresets(false);
  }

  function moveQuestion(idx: number, dir: -1 | 1) {
    if (idx + dir < 0 || idx + dir >= value.length) return;
    const updated = [...value];
    [updated[idx], updated[idx + dir]] = [updated[idx + dir], updated[idx]];
    onChange(updated);
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">报名问卷</label>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" className="text-xs" onClick={() => setShowPresets(!showPresets)}>
            常用问题
          </Button>
          <Button type="button" variant="outline" size="sm" className="text-xs" onClick={addQuestion}>
            + 添加问题
          </Button>
        </div>
      </div>

      {showPresets && (
        <div className="mt-2 rounded-lg border bg-muted/30 p-3 space-y-1.5">
          <p className="text-xs text-muted-foreground mb-1">点击一键添加：</p>
          {PRESET_QUESTIONS.map((p, i) => (
            <button
              key={i}
              type="button"
              onClick={() => addPreset(p)}
              className="block w-full text-left rounded px-2.5 py-1.5 text-sm hover:bg-muted transition-colors"
            >
              {p.question_text}
              <span className="ml-2 text-xs text-muted-foreground">
                {p.question_type === "text" ? "文本" : p.question_type === "select" ? "单选" : "多选"}
              </span>
            </button>
          ))}
        </div>
      )}

      {value.length > 0 && (
        <div className="mt-3 space-y-3">
          {value.map((q, idx) => (
            <div key={idx} className="rounded-lg border p-3 space-y-2.5 bg-card">
              <div className="flex items-start gap-2">
                <span className="text-xs text-muted-foreground mt-2 w-5 text-right shrink-0">{idx + 1}.</span>
                <div className="flex-1 space-y-2">
                  <Input
                    value={q.question_text}
                    onChange={(e) => updateQuestion(idx, "question_text", e.target.value)}
                    placeholder="输入问题..."
                    className="text-sm"
                  />
                  <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex gap-1">
                      {(["text", "select", "multiselect"] as const).map((t) => (
                        <button
                          key={t}
                          type="button"
                          onClick={() => updateQuestion(idx, "question_type", t)}
                          className={`rounded px-2 py-0.5 text-xs transition-colors ${
                            q.question_type === t
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted hover:bg-muted/80"
                          }`}
                        >
                          {{ text: "文本", select: "单选", multiselect: "多选" }[t]}
                        </button>
                      ))}
                    </div>
                    <label className="flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={q.is_required}
                        onChange={(e) => updateQuestion(idx, "is_required", e.target.checked)}
                        className="h-3.5 w-3.5 rounded border-input"
                      />
                      <span className="text-xs">必填</span>
                    </label>
                  </div>

                  {(q.question_type === "select" || q.question_type === "multiselect") && (
                    <div className="space-y-1.5 pl-1">
                      {q.options.map((opt, optIdx) => (
                        <div key={optIdx} className="flex items-center gap-1.5">
                          <span className="text-xs text-muted-foreground w-4">
                            {q.question_type === "select" ? "○" : "□"}
                          </span>
                          <Input
                            value={opt}
                            onChange={(e) => updateOption(idx, optIdx, e.target.value)}
                            placeholder={`选项 ${optIdx + 1}`}
                            className="text-xs h-7 flex-1"
                          />
                          <button
                            type="button"
                            onClick={() => removeOption(idx, optIdx)}
                            className="text-xs text-muted-foreground hover:text-destructive px-1"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                      <div className="flex items-center gap-3 pl-5">
                        <button
                          type="button"
                          onClick={() => addOption(idx)}
                          className="text-xs text-primary hover:underline"
                        >
                          + 添加选项
                        </button>
                        {!q.options.includes("其他（请说明）") && (
                          <button
                            type="button"
                            onClick={() => addOtherOption(idx)}
                            className="text-xs text-muted-foreground hover:text-primary hover:underline"
                          >
                            + 其他选项
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-0.5 shrink-0">
                  <button type="button" onClick={() => moveQuestion(idx, -1)} className="text-xs text-muted-foreground hover:text-foreground px-1" title="上移">↑</button>
                  <button type="button" onClick={() => moveQuestion(idx, 1)} className="text-xs text-muted-foreground hover:text-foreground px-1" title="下移">↓</button>
                  <button type="button" onClick={() => removeQuestion(idx)} className="text-xs text-muted-foreground hover:text-destructive px-1" title="删除">×</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {value.length === 0 && (
        <p className="mt-2 text-xs text-muted-foreground">
          未设置问卷。报名者只需点击报名即可。
        </p>
      )}
    </div>
  );
}

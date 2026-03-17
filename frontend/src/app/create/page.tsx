"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { ImageUpload } from "@/components/image-upload";
import { DescriptionEditor } from "@/components/description-editor";
import { QuestionConfigurator, QuestionDraft } from "@/components/question-configurator";
import { ThemePicker } from "@/components/theme-picker";
import { getThemeById, getThemeCoverStyle } from "@/lib/themes";
import { buildISOInTZ } from "@/lib/date-utils";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

export default function CreateEventPage() {
  const { authenticated } = useRequireAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState("");
  const [customQuestions, setCustomQuestions] = useState<QuestionDraft[]>([]);
  const [themePreset, setThemePreset] = useState("");
  const [form, setForm] = useState({
    title: "",
    organizer_name: "",
    description: "",
    cover_image_url: "",
    event_type: "in_person",
    location_name: "",
    location_address: "",
    online_url: "",
    start_date: "",
    start_time: "09:00",
    end_date: "",
    end_time: "18:00",
    capacity: "",
    registration_limit: "",
    reg_deadline_date: "",
    reg_deadline_time: "23:59",
    require_approval: false,
    notify_on_register: false,
    allow_self_checkin: true,
  });

  function update(field: string, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  if (!authenticated) {
    return <div className="mx-auto max-w-2xl px-4 py-10"><p className="text-muted-foreground">正在跳转登录...</p></div>;
  }

  async function handleAIGenerate(extraPrompt?: string) {
    if (!form.title.trim()) {
      setError("请先填写活动名称");
      return;
    }
    setAiLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/v1/events/generate-description`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          title: form.title,
          event_type: form.event_type,
          location: form.location_name || undefined,
          start_time: form.start_date ? `${form.start_date} ${form.start_time}` : undefined,
          existing_description: form.description || undefined,
          user_prompt: extraPrompt || undefined,
        }),
      });
      const data = await res.json();
      if (data.success) {
        update("description", data.description);
      } else {
        setError(data.detail || "AI 生成失败");
      }
    } catch {
      setError("AI 生成失败，请重试");
    } finally {
      setAiLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const start_time = form.start_date && form.start_time
      ? buildISOInTZ(form.start_date, form.start_time)
      : null;
    const end_time = form.end_date && form.end_time
      ? buildISOInTZ(form.end_date, form.end_time)
      : null;

    if (!start_time) {
      setError("请选择开始日期和时间");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API}/api/v1/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          title: form.title,
          organizer_name: form.organizer_name.trim() || null,
          description: form.description || null,
          cover_image_url: form.cover_image_url || null,
          event_type: form.event_type,
          location_name: form.location_name || null,
          location_address: form.location_address || null,
          online_url: form.online_url || null,
          start_time,
          end_time,
          capacity: form.capacity ? parseInt(form.capacity) : null,
          registration_limit: form.registration_limit ? parseInt(form.registration_limit) : null,
          registration_deadline: form.reg_deadline_date
            ? buildISOInTZ(form.reg_deadline_date, form.reg_deadline_time)
            : null,
          require_approval: form.require_approval,
          notify_on_register: form.notify_on_register,
          allow_self_checkin: form.allow_self_checkin,
          theme: themePreset ? { preset: themePreset } : {},
          custom_questions: customQuestions.filter((q) => q.question_text.trim()).length > 0
            ? customQuestions
                .filter((q) => q.question_text.trim())
                .map((q) => ({
                  question_text: q.question_text,
                  question_type: q.question_type,
                  options: q.options.length > 0 ? q.options.filter(Boolean) : undefined,
                  is_required: q.is_required,
                }))
            : undefined,
        }),
      });
      const data = await res.json();
      if (data.success) {
        router.push(`/e/${data.data.slug}`);
      } else {
        setError(data.detail || "创建失败");
      }
    } catch {
      setError("网络错误");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-3xl font-bold tracking-tight">创建活动</h1>
      <p className="mt-2 text-muted-foreground">填写活动信息，创建后可编辑发布。</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        {/* Cover Image */}
        <ImageUpload
          value={form.cover_image_url}
          onChange={(url) => { update("cover_image_url", url); if (url) setThemePreset(""); }}
          themeStyle={themePreset ? getThemeCoverStyle(getThemeById(themePreset)!) : undefined}
        />

        {/* Theme Picker */}
        <ThemePicker
          value={themePreset}
          onChange={(id) => { setThemePreset(id); if (id) update("cover_image_url", ""); }}
          disabled={!!form.cover_image_url}
        />

        {/* Title */}
        <div>
          <label className="text-sm font-medium">活动名称 *</label>
          <Input
            value={form.title}
            onChange={(e) => update("title", e.target.value)}
            placeholder="如：虾聊 AI Agent Hackathon"
            required
            className="mt-1.5"
          />
        </div>

        {/* Organizer Name */}
        <div>
          <label className="text-sm font-medium">主办方名称</label>
          <Input
            value={form.organizer_name}
            onChange={(e) => update("organizer_name", e.target.value)}
            placeholder="如：虾聊官方（不填则使用账号昵称）"
            className="mt-1.5"
            maxLength={200}
          />
        </div>

        {/* Description */}
        <DescriptionEditor
          value={form.description}
          onChange={(v) => update("description", v)}
          onAIGenerate={handleAIGenerate}
          aiLoading={aiLoading}
        />

        {/* Type */}
        <div>
          <label className="text-sm font-medium">活动类型</label>
          <div className="mt-1.5 flex gap-3">
            {[
              { value: "in_person", label: "线下" },
              { value: "online", label: "线上" },
              { value: "hybrid", label: "混合" },
            ].map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => update("event_type", opt.value)}
                className={`rounded-lg border px-4 py-2 text-sm transition-colors ${
                  form.event_type === opt.value
                    ? "border-primary bg-primary text-primary-foreground"
                    : "hover:bg-muted"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Location */}
        {(form.event_type === "in_person" || form.event_type === "hybrid") && (
          <div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm font-medium">地点名称</label>
                <Input
                  value={form.location_name}
                  onChange={(e) => update("location_name", e.target.value)}
                  placeholder="如：虾聊总部"
                  className="mt-1.5"
                />
              </div>
              <div>
                <label className="text-sm font-medium">详细地址</label>
                <Input
                  value={form.location_address}
                  onChange={(e) => update("location_address", e.target.value)}
                  placeholder="如：上海市浦东新区张杨路500号5楼"
                  className="mt-1.5"
                />
              </div>
            </div>
            {form.require_approval && (
              <p className="mt-1.5 text-xs text-amber-600">
                🔒 开启审批后，详细地址仅对审批通过的报名者可见，其他用户只能看到大致位置。请填写精确到门牌号的完整地址。
              </p>
            )}
          </div>
        )}

        {/* Online URL */}
        {(form.event_type === "online" || form.event_type === "hybrid") && (
          <div>
            <label className="text-sm font-medium">线上链接</label>
            <Input
              value={form.online_url}
              onChange={(e) => update("online_url", e.target.value)}
              placeholder="https://..."
              className="mt-1.5"
            />
          </div>
        )}

        {/* Date & Time */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-sm font-medium">开始日期 *</label>
            <Input
              type="date"
              value={form.start_date}
              onChange={(e) => update("start_date", e.target.value)}
              required
              className="mt-1.5"
            />
          </div>
          <div>
            <label className="text-sm font-medium">开始时间</label>
            <Input
              type="time"
              value={form.start_time}
              onChange={(e) => update("start_time", e.target.value)}
              className="mt-1.5"
            />
          </div>
          <div>
            <label className="text-sm font-medium">结束日期</label>
            <Input
              type="date"
              value={form.end_date}
              onChange={(e) => update("end_date", e.target.value)}
              className="mt-1.5"
            />
          </div>
          <div>
            <label className="text-sm font-medium">结束时间</label>
            <Input
              type="time"
              value={form.end_time}
              onChange={(e) => update("end_time", e.target.value)}
              className="mt-1.5"
            />
          </div>
        </div>

        {/* Registration Deadline */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-sm font-medium">报名截止日期</label>
            <Input
              type="date"
              value={form.reg_deadline_date}
              onChange={(e) => update("reg_deadline_date", e.target.value)}
              className="mt-1.5"
            />
            <p className="mt-0.5 text-xs text-muted-foreground">不填则不限截止时间</p>
          </div>
          <div>
            <label className="text-sm font-medium">截止时间</label>
            <Input
              type="time"
              value={form.reg_deadline_time}
              onChange={(e) => update("reg_deadline_time", e.target.value)}
              className="mt-1.5"
            />
          </div>
        </div>

        {/* Capacity & Registration Limit & Approval & Notification */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-sm font-medium">活动人数</label>
            <Input
              type="number"
              value={form.capacity}
              onChange={(e) => update("capacity", e.target.value)}
              placeholder="预计参与人数（展示用）"
              min={1}
              className="mt-1.5"
            />
          </div>
          <div>
            <label className="text-sm font-medium">报名上限</label>
            <Input
              type="number"
              value={form.registration_limit}
              onChange={(e) => update("registration_limit", e.target.value)}
              placeholder="不填则无限制"
              min={1}
              className="mt-1.5"
            />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2 justify-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.require_approval}
                onChange={(e) => update("require_approval", e.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              <span className="text-sm font-medium">需要审批报名</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.notify_on_register}
                onChange={(e) => update("notify_on_register", e.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              <span className="text-sm font-medium">有人报名时通知我</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.allow_self_checkin}
                onChange={(e) => update("allow_self_checkin", e.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              <span className="text-sm font-medium">允许自助签到</span>
            </label>
          </div>
        </div>

        {/* Custom Questions */}
        <QuestionConfigurator value={customQuestions} onChange={setCustomQuestions} />

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button type="submit" disabled={loading} size="lg" className="w-full">
          {loading ? "创建中..." : "创建活动"}
        </Button>
      </form>
    </div>
  );
}

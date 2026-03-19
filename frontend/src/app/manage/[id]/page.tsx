"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useRequireAuth } from "@/hooks/use-require-auth";
import { QrScanner } from "@/components/qr-scanner";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

interface EventInfo {
  id: string;
  title: string;
  slug: string;
  status: string;
  start_time: string;
  end_time: string | null;
  location_name: string | null;
  event_type: string;
  registration_count: number;
  capacity: number | null;
  circle_id: string | null;
}

interface Registration {
  id: string;
  user: { id: string; nickname: string; phone: string; email?: string } | null;
  agent: { id: string; name: string; display_name: string } | null;
  status: string;
  registered_via: string;
  custom_answers: Record<string, string | string[]> | null;
  qr_code_token: string;
  registered_at: string;
  checked_in_at: string | null;
}

interface AnswerStat {
  question_id: string;
  question_text: string;
  question_type: string;
  options: string[] | null;
  stats: Record<string, number>;
  total_answers: number;
}

interface StaffMember {
  id: string;
  agent_name: string | null;
  agent_display_name: string | null;
  role: string;
}

interface WinnerInfo {
  id: string;
  rank: number | null;
  prize_name: string | null;
  user: { id: string | null; nickname: string | null } | null;
  agent: { name: string | null } | null;
}

const statusLabels: Record<string, string> = {
  draft: "草稿",
  published: "已发布",
  offline: "已下线",
  cancelled: "已取消",
  completed: "已结束",
};

const PERM_LABELS: Record<string, string> = {
  checkin: "签到",
  view_registrations: "查看报名",
  approve_registrations: "审批报名",
  export_csv: "导出 CSV",
  view_stats: "问卷统计",
  view_cohosts: "查看联合主办方",
  view_staff: "查看 Staff",
  view_winners: "查看获奖者",
  view_checkin_key: "查看签到密钥",
};

const OPTIONAL_PERMS = Object.entries(PERM_LABELS).filter(([k]) => k !== "checkin");

function PermissionCheckboxes({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <input type="checkbox" checked disabled className="h-3.5 w-3.5" />
        签到（默认）
      </label>
      {OPTIONAL_PERMS.map(([key, label]) => (
        <label key={key} className="flex items-center gap-2 text-xs cursor-pointer">
          <input
            type="checkbox"
            className="h-3.5 w-3.5"
            checked={value.includes(key)}
            onChange={(e) => {
              if (e.target.checked) {
                onChange([...value, key]);
              } else {
                onChange(value.filter((v) => v !== key));
              }
            }}
          />
          {label}
        </label>
      ))}
    </div>
  );
}

export default function ManagePage() {
  const { authenticated, user: currentUser } = useRequireAuth();
  const params = useParams();
  const router = useRouter();
  const eventId = params.id as string;

  const [event, setEvent] = useState<EventInfo | null>(null);
  const [regs, setRegs] = useState<Registration[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [expandedReg, setExpandedReg] = useState<string | null>(null);
  const [answerStats, setAnswerStats] = useState<AnswerStat[]>([]);
  const [showStats, setShowStats] = useState(false);
  const [answerFilter, setAnswerFilter] = useState<{ questionId: string; value: string } | null>(null);

  const [actionLoading, setActionLoading] = useState("");
  const [confirmDialog, setConfirmDialog] = useState<{ type: string; regId?: string } | null>(null);
  const [syncToClawdchat, setSyncToClawdchat] = useState(true);

  // Role & permissions
  const [myRole, setMyRole] = useState<"host" | "cohost" | null>(null);
  const [myPerms, setMyPerms] = useState<string[]>([]);
  const isHost = myRole === "host";
  const hasPerm = (p: string) => isHost || myPerms.includes(p);

  // Blast notification state
  const [showBlast, setShowBlast] = useState(false);
  const [blastContent, setBlastContent] = useState("");
  const [blastChannels, setBlastChannels] = useState<string[]>(["sms"]);
  const [blastLoading, setBlastLoading] = useState(false);
  const [blastResult, setBlastResult] = useState<string | null>(null);
  const [smsTemplates, setSmsTemplates] = useState<{ type: string; label: string; variables: string[]; preview: string; configured: boolean }[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState("registration_success");
  const [smsVars, setSmsVars] = useState<Record<string, string>>({});
  const [smsVarsInited, setSmsVarsInited] = useState(false);
  const [testPhones, setTestPhones] = useState("");
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  // Feedback state
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackData, setFeedbackData] = useState<{ avg_rating: number; count: number; items: { id: string; rating: number; comment: string | null; user: { nickname: string | null }; created_at: string | null }[] }>({ avg_rating: 0, count: 0, items: [] });

  // Co-host state
  const [showCohosts, setShowCohosts] = useState(false);
  const [cohosts, setCohosts] = useState<{ id: string; user_id: string | null; nickname: string | null; avatar_url: string | null; permissions: string[] }[]>([]);
  const [newCohostPhone, setNewCohostPhone] = useState("");
  const [newCohostPerms, setNewCohostPerms] = useState<string[]>([]);
  const [cohostLoading, setCohostLoading] = useState(false);
  const [cohostError, setCohostError] = useState("");
  const [editingCohostId, setEditingCohostId] = useState<string | null>(null);
  const [editingPerms, setEditingPerms] = useState<string[]>([]);

  // Staff state
  const [showStaff, setShowStaff] = useState(false);
  const [staffList, setStaffList] = useState<StaffMember[]>([]);
  const [newStaffName, setNewStaffName] = useState("");
  const [staffLoading, setStaffLoading] = useState(false);

  // Winners state
  const [showWinners, setShowWinners] = useState(false);
  const [winners, setWinners] = useState<WinnerInfo[]>([]);

  // Check-in scanner state
  const [showCheckin, setShowCheckin] = useState(false);
  const [scanLoading, setScanLoading] = useState(false);
  const [scanResult, setScanResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [checkinKey, setCheckinKey] = useState<string | null>(null);
  const [checkinKeyLoading, setCheckinKeyLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showRegs, setShowRegs] = useState(false);

  async function loadMyRole() {
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/my-role`, { credentials: "include" });
      const data = await res.json();
      if (data.success && data.data) {
        setMyRole(data.data.role);
        setMyPerms(data.data.permissions || []);
      }
    } catch { /* ignore */ }
  }

  async function loadEvent() {
    try {
      const res = await fetch(`${API}/api/v1/events/${eventId}`, { credentials: "include" });
      const data = await res.json();
      if (data.success && data.data) setEvent(data.data);
    } catch { /* ignore */ }
  }

  async function loadData() {
    try {
      const regRes = await fetch(`${API}/api/v1/host/events/${eventId}/registrations?limit=200`, { credentials: "include" });
      const allRegs = await regRes.json();
      if (allRegs.data) setRegs(allRegs.data);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }

  async function loadStats() {
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/answer-stats`, { credentials: "include" });
      const data = await res.json();
      if (data.data) setAnswerStats(data.data);
    } catch { /* ignore */ }
  }

  async function loadFeedback() {
    try {
      if (!event?.slug) return;
      const res = await fetch(`${API}/api/v1/events/${event.slug}/feedback`);
      const data = await res.json();
      if (data.success && data.data) setFeedbackData(data.data);
    } catch { /* ignore */ }
  }

  async function loadCohosts() {
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/cohosts`, { credentials: "include" });
      const data = await res.json();
      if (data.data) setCohosts(data.data);
    } catch { /* ignore */ }
  }

  async function handleAddCohost() {
    if (!newCohostPhone.trim()) return;
    setCohostLoading(true);
    setCohostError("");
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/cohosts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ phone: newCohostPhone.trim(), permissions: ["checkin", ...newCohostPerms] }),
      });
      const data = await res.json();
      if (data.success) {
        setNewCohostPhone("");
        setNewCohostPerms([]);
        loadCohosts();
      } else {
        setCohostError(data.detail || "添加失败，请重试");
      }
    } catch {
      setCohostError("网络错误，请重试");
    } finally { setCohostLoading(false); }
  }

  async function handleRemoveCohost(cohostId: string) {
    await fetch(`${API}/api/v1/host/events/${eventId}/cohosts/${cohostId}`, {
      method: "DELETE", credentials: "include",
    });
    loadCohosts();
  }

  async function handleUpdateCohostPerms(cohostId: string, perms: string[]) {
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/cohosts/${cohostId}/permissions`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ permissions: ["checkin", ...perms] }),
      });
      const data = await res.json();
      if (data.success) {
        loadCohosts();
        setEditingCohostId(null);
      }
    } catch { /* ignore */ }
  }

  async function loadStaff() {
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/staff`, { credentials: "include" });
      const data = await res.json();
      if (data.data) setStaffList(data.data);
    } catch { /* ignore */ }
  }

  async function loadWinners() {
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/winners`, { credentials: "include" });
      const data = await res.json();
      if (data.data) setWinners(data.data);
    } catch { /* ignore */ }
  }

  async function handleAddStaff() {
    if (!newStaffName.trim()) return;
    setStaffLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/staff`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ agent_name: newStaffName.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        setNewStaffName("");
        loadStaff();
      }
    } finally { setStaffLoading(false); }
  }

  async function handleRemoveStaff(staffId: string) {
    await fetch(`${API}/api/v1/host/events/${eventId}/staff/${staffId}`, {
      method: "DELETE", credentials: "include",
    });
    loadStaff();
  }

  async function filterByAnswer(questionId: string, value: string) {
    setAnswerFilter({ questionId, value });
    try {
      const res = await fetch(
        `${API}/api/v1/host/events/${eventId}/registrations/filter-by-answer?question_id=${questionId}&answer_value=${encodeURIComponent(value)}`,
        { credentials: "include" }
      );
      const data = await res.json();
      if (data.data) setRegs(data.data);
    } catch { /* ignore */ }
  }

  function clearAnswerFilter() {
    setAnswerFilter(null);
    loadData();
  }

  async function loadCheckinKey() {
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/checkin-key`, { credentials: "include" });
      const data = await res.json();
      if (data.success) setCheckinKey(data.data.checkin_key || null);
    } catch { /* ignore */ }
  }

  async function handleGenerateCheckinKey() {
    setCheckinKeyLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/checkin-key`, {
        method: "POST", credentials: "include",
      });
      const data = await res.json();
      if (data.success) setCheckinKey(data.data.checkin_key);
    } finally { setCheckinKeyLoading(false); }
  }

  async function handleRevokeCheckinKey() {
    setCheckinKeyLoading(true);
    try {
      await fetch(`${API}/api/v1/host/events/${eventId}/checkin-key`, {
        method: "DELETE", credentials: "include",
      });
      setCheckinKey(null);
    } finally { setCheckinKeyLoading(false); }
  }

  function getStaffCheckinUrl() {
    if (!checkinKey) return "";
    const base = typeof window !== "undefined" ? window.location.origin : "";
    return `${base}/checkin-staff/${eventId}?key=${checkinKey}`;
  }

  async function copyCheckinLink() {
    const url = getStaffCheckinUrl();
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  useEffect(() => {
    if (authenticated) {
      loadEvent();
      loadMyRole();
      loadData();
      loadStats();
      loadCohosts();
      loadStaff();
      loadWinners();
      loadCheckinKey();
      loadSmsTemplates();
    }
  }, [eventId, authenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadSmsTemplates() {
    try {
      const res = await fetch(`${API}/api/v1/notify/sms-templates`, { credentials: "include" });
      const data = await res.json();
      if (data.success) setSmsTemplates(data.data);
    } catch { /* ignore */ }
  }

  async function handlePublish() {
    setActionLoading("publish");
    try {
      await fetch(`${API}/api/v1/events/${eventId}/publish`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sync_to_clawdchat: syncToClawdchat }),
      });
      await loadEvent();
    } finally { setActionLoading(""); }
  }

  async function handleSyncClawdchat() {
    setActionLoading("sync");
    try {
      await fetch(`${API}/api/v1/events/${eventId}/sync-clawdchat`, {
        method: "POST",
        credentials: "include",
      });
      await loadEvent();
    } finally { setActionLoading(""); }
  }

  async function handleCancel() {
    setActionLoading("cancel");
    try {
      await fetch(`${API}/api/v1/events/${eventId}/cancel`, { method: "POST", credentials: "include" });
      await loadEvent();
    } finally {
      setActionLoading("");
      setConfirmDialog(null);
    }
  }

  async function handleOffline() {
    setActionLoading("offline");
    try {
      await fetch(`${API}/api/v1/events/${eventId}/offline`, { method: "POST", credentials: "include" });
      await loadEvent();
    } finally {
      setActionLoading("");
      setConfirmDialog(null);
    }
  }

  async function handleOnline() {
    setActionLoading("online");
    try {
      await fetch(`${API}/api/v1/events/${eventId}/online`, { method: "POST", credentials: "include" });
      await loadEvent();
    } finally { setActionLoading(""); }
  }

  async function handleDelete() {
    setActionLoading("delete");
    try {
      const res = await fetch(`${API}/api/v1/events/${eventId}`, { method: "DELETE", credentials: "include" });
      const data = await res.json();
      if (data.success) {
        router.push("/my");
        return;
      }
    } finally {
      setActionLoading("");
      setConfirmDialog(null);
    }
  }

  async function handleClone() {
    setActionLoading("clone");
    try {
      const res = await fetch(`${API}/api/v1/events/${eventId}/clone`, { method: "POST", credentials: "include" });
      const data = await res.json();
      if (data.success && data.data) {
        router.push(`/edit/${data.data.id}`);
      }
    } finally { setActionLoading(""); }
  }

  const lastScannedRef = useRef<string>("");
  const scanTimerRef = useRef<ReturnType<typeof setTimeout>>();

  async function handleScanCheckin(token: string) {
    const t = token.trim();
    if (!t) return;
    if (t === lastScannedRef.current) return;
    lastScannedRef.current = t;
    setScanLoading(true);
    setScanResult(null);
    try {
      const res = await fetch(`${API}/api/v1/checkin/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ qr_token: t }),
      });
      const data = await res.json();
      if (data.success) {
        setScanResult({ ok: true, message: data.data.message });
        loadData();
      } else {
        setScanResult({ ok: false, message: data.detail || "签到失败" });
      }
    } catch {
      setScanResult({ ok: false, message: "网络错误" });
    } finally {
      setScanLoading(false);
      clearTimeout(scanTimerRef.current);
      scanTimerRef.current = setTimeout(() => {
        lastScannedRef.current = "";
        setScanResult(null);
      }, 3000);
    }
  }

  async function handleApprove(regId: string) {
    await fetch(`${API}/api/v1/host/events/${eventId}/registrations/${regId}/approve`, {
      method: "POST", credentials: "include",
    });
    loadData();
  }

  async function handleDecline(regId: string) {
    setConfirmDialog(null);
    await fetch(`${API}/api/v1/host/events/${eventId}/registrations/${regId}/decline`, {
      method: "POST", credentials: "include",
    });
    loadData();
  }

  async function handleWaitlist(regId: string) {
    await fetch(`${API}/api/v1/host/events/${eventId}/registrations/${regId}/waitlist`, {
      method: "POST", credentials: "include",
    });
    loadData();
  }

  async function handleBatchApprove() {
    await fetch(`${API}/api/v1/host/events/${eventId}/registrations/batch-approve`, {
      method: "POST", credentials: "include",
    });
    loadData();
  }

  async function handleExport() {
    const res = await fetch(`${API}/api/v1/host/events/${eventId}/registrations/export`, {
      credentials: "include",
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `registrations-${eventId}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  const VAR_LABELS: Record<string, string> = { event: "活动名", time: "时间", location: "地点" };

  function getEventDefaults(): Record<string, string> {
    if (!event) return {};
    const fmt = (t: string | undefined) => {
      if (!t) return "待定";
      const d = new Date(t);
      return `${d.getMonth() + 1}月${d.getDate()}日 ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
    };
    return { event: event.title || "", time: fmt(event.start_time), location: event.location_name || "线上" };
  }

  if (event && !smsVarsInited) {
    setSmsVars(getEventDefaults());
    setSmsVarsInited(true);
  }

  const currentTemplate = smsTemplates.find((t) => t.type === selectedTemplate);

  function renderSmsPreview() {
    if (!currentTemplate) return "";
    let text = currentTemplate.preview;
    for (const v of currentTemplate.variables) {
      text = text.replace(`\${${v}}`, smsVars[v] || "");
    }
    return text;
  }

  async function handleBlast(channels: string[]) {
    const needContent = channels.includes("a2a");
    if (needContent && !blastContent.trim()) return;
    if (channels.length === 0) return;
    setBlastChannels(channels);
    setBlastLoading(true);
    setBlastResult(null);
    try {
      const res = await fetch(`${API}/api/v1/notify/events/${eventId}/blast`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          subject: smsVars.event || event?.title || "",
          content: blastContent.trim() || smsVars.event || "",
          channels,
          target_status: "approved",
          sms_template_type: selectedTemplate,
          sms_params: smsVars,
        }),
      });
      const data = await res.json();
      if (data.success) {
        const d = data.data;
        setBlastResult(`发送完成：${d.sent}/${d.total_recipients} 人成功`);
        if (channels.includes("a2a")) setBlastContent("");
      } else {
        setBlastResult(data.detail || "发送失败");
      }
    } catch {
      setBlastResult("网络错误");
    } finally {
      setBlastLoading(false);
    }
  }

  async function handleTestSms() {
    const phones = testPhones.split(/[,，\s]+/).filter(Boolean);
    if (phones.length === 0 || phones.length > 3) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API}/api/v1/notify/events/${eventId}/blast/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          phones,
          sms_template_type: selectedTemplate,
          sms_params: smsVars,
        }),
      });
      const data = await res.json();
      if (data.success) {
        const results = data.data as { phone: string; success: boolean; error?: string }[];
        const ok = results.filter((r) => r.success).length;
        setTestResult(`测试发送：${ok}/${results.length} 条成功`);
      } else {
        setTestResult(data.detail || "测试失败");
      }
    } catch {
      setTestResult("网络错误");
    } finally {
      setTestLoading(false);
    }
  }

  const filteredRegs = filter === "all" ? regs : regs.filter((r) => r.status === filter);
  const pendingCount = regs.filter((r) => r.status === "pending").length;
  const approvedCount = regs.filter((r) => r.status === "approved").length;
  const declinedCount = regs.filter((r) => r.status === "declined").length;
  const waitlistedCount = regs.filter((r) => r.status === "waitlisted").length;
  const checkedInCount = regs.filter((r) => r.checked_in_at).length;
  const statusCounts: Record<string, number> = {
    all: regs.length,
    pending: pendingCount,
    approved: approvedCount,
    declined: declinedCount,
    waitlisted: waitlistedCount,
  };

  if (loading) {
    return <div className="mx-auto max-w-4xl px-4 py-10"><p className="text-muted-foreground">加载中...</p></div>;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      {/* Event Header */}
      {event && (
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Badge variant={event.status === "published" ? "default" : event.status === "draft" ? "secondary" : event.status === "offline" ? "destructive" : "outline"}>
              {statusLabels[event.status] || event.status}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {new Date(event.start_time).toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" })}
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{event.title}</h1>
          {event.location_name && (
            <p className="text-sm text-muted-foreground mt-1">{event.location_name}</p>
          )}
        </div>
      )}

      {/* Co-host role badge & permissions */}
      {myRole === "cohost" && (
        <div className="mb-4 space-y-2">
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-200">
            你是此活动的联合主办方
          </div>
          {(() => {
            const myCohost = cohosts.find((ch) => ch.user_id === currentUser?.id);
            if (!myCohost) return null;
            return (
              <Card>
                <CardContent className="p-4">
                  <p className="text-sm font-medium mb-2">我的权限</p>
                  <div className="flex flex-wrap gap-1">
                    {(myCohost.permissions || ["checkin"]).map((p: string) => (
                      <span key={p} className="inline-block rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                        {PERM_LABELS[p] || p}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })()}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        {isHost && event?.status === "draft" && (
          <>
            <label className="flex items-center gap-1.5 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                checked={syncToClawdchat}
                onChange={(e) => setSyncToClawdchat(e.target.checked)}
                className="rounded border-gray-300"
              />
              同步到虾聊
            </label>
            <Button onClick={handlePublish} disabled={actionLoading === "publish"}>
              {actionLoading === "publish" ? "发布中..." : "发布活动"}
            </Button>
          </>
        )}
        {isHost && event?.status === "published" && !event.circle_id && (
          <Button variant="outline" onClick={handleSyncClawdchat} disabled={actionLoading === "sync"}>
            {actionLoading === "sync" ? "同步中..." : "同步到虾聊"}
          </Button>
        )}
        {event && (
          <Link href={`/e/${event.slug}`}>
            <Button variant="outline">查看活动页</Button>
          </Link>
        )}
        {isHost && event && (event.status === "draft" || event.status === "published" || event.status === "offline") && (
          <Link href={`/edit/${event.id}`}>
            <Button variant="outline">编辑活动</Button>
          </Link>
        )}
        {hasPerm("export_csv") && (
          <Button variant="outline" onClick={handleExport}>导出 CSV</Button>
        )}
        {isHost && (
          <Button
            variant="outline"
            onClick={handleClone}
            disabled={actionLoading === "clone"}
          >
            {actionLoading === "clone" ? "克隆中..." : "克隆活动"}
          </Button>
        )}
        {isHost && event?.status === "published" && (
          <Button
            variant="outline"
            className="text-orange-600 hover:text-orange-600"
            onClick={() => setConfirmDialog({ type: "offline" })}
            disabled={actionLoading === "offline"}
          >
            {actionLoading === "offline" ? "下线中..." : "暂时下线"}
          </Button>
        )}
        {isHost && event?.status === "offline" && (
          <Button
            variant="outline"
            className="text-green-600 hover:text-green-600"
            onClick={handleOnline}
            disabled={actionLoading === "online"}
          >
            {actionLoading === "online" ? "上线中..." : "重新上线"}
          </Button>
        )}
        {isHost && event?.status === "published" && (
          <Button
            variant="outline"
            className="text-destructive hover:text-destructive"
            onClick={() => setConfirmDialog({ type: "cancel" })}
          >
            取消活动
          </Button>
        )}
        {isHost && event && (event.status === "draft" || event.status === "cancelled") && (
          <Button
            variant="outline"
            className="text-destructive hover:text-destructive"
            onClick={() => setConfirmDialog({ type: "delete" })}
          >
            删除活动
          </Button>
        )}
      </div>

      {/* Stats Cards */}
      {hasPerm("view_registrations") && <div className="grid grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{regs.length}</p>
            <p className="text-xs text-muted-foreground">总报名</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{approvedCount}</p>
            <p className="text-xs text-muted-foreground">已通过</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{pendingCount}</p>
            <p className="text-xs text-muted-foreground">待审批</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{checkedInCount}</p>
            <p className="text-xs text-muted-foreground">已签到</p>
          </CardContent>
        </Card>
      </div>}

      {/* Check-in Scanner & Staff Link */}
      {event?.status === "published" && (
        <div className="mb-6">
          <button
            onClick={() => { setShowCheckin(!showCheckin); setScanResult(null); }}
            className="text-sm font-medium text-primary hover:underline"
          >
            {showCheckin ? "收起" : "展开"}签到管理
          </button>
          {showCheckin && (
            <div className="mt-3 space-y-3">
              {/* Staff check-in link */}
              {isHost && (
                <Card>
                  <CardContent className="p-4 space-y-3">
                    <p className="text-sm font-medium">工作人员签到链接</p>
                    <p className="text-xs text-muted-foreground">
                      生成链接发给工作人员，无需登录即可用手机扫码签到
                    </p>
                    {checkinKey ? (
                      <div className="space-y-2">
                        <div className="flex gap-2">
                          <Input
                            readOnly
                            value={getStaffCheckinUrl()}
                            className="text-xs bg-muted flex-1"
                            onFocus={(e) => e.target.select()}
                          />
                          <Button size="sm" variant="outline" onClick={copyCheckinLink}>
                            {copied ? "已复制" : "复制"}
                          </Button>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleGenerateCheckinKey}
                            disabled={checkinKeyLoading}
                          >
                            重新生成
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-destructive"
                            onClick={handleRevokeCheckinKey}
                            disabled={checkinKeyLoading}
                          >
                            废弃链接
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        onClick={handleGenerateCheckinKey}
                        disabled={checkinKeyLoading}
                      >
                        {checkinKeyLoading ? "生成中..." : "生成签到链接"}
                      </Button>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Host/cohost self-scan */}
              <Card>
                <CardContent className="p-4 space-y-3">
                  <p className="text-sm font-medium">扫码签到</p>
                  <p className="text-xs text-muted-foreground">
                    用手机摄像头扫描参会者的签到二维码
                  </p>
                  <QrScanner
                    onScan={(text) => handleScanCheckin(text)}
                    paused={scanLoading}
                  />
                  {scanResult && (
                    <div className={`rounded-lg p-3 text-center text-sm font-medium ${
                      scanResult.ok ? "bg-green-50 text-green-700" : "bg-red-50 text-destructive"
                    }`}>
                      {scanResult.message}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Blast Notification */}
      {isHost && <div className="mb-6">
        <button
          onClick={() => setShowBlast(!showBlast)}
          className="text-sm font-medium text-primary hover:underline"
        >
          {showBlast ? "收起" : "展开"}群发通知
        </button>
        {showBlast && (
          <Card className="mt-3">
            <CardContent className="p-4 space-y-4">
              {/* SMS blast */}
              <div className="space-y-2">
                <p className="text-sm font-medium">短信群发</p>
                <p className="text-xs text-muted-foreground">审批通过时已自动发送报名成功短信，此处可选择模板群发或补发</p>
                <select
                  value={selectedTemplate}
                  onChange={(e) => {
                    setSelectedTemplate(e.target.value);
                    setSmsVars(getEventDefaults());
                  }}
                  className="w-full h-8 text-sm border rounded-md px-2 bg-background"
                >
                  {smsTemplates.map((t) => (
                    <option key={t.type} value={t.type} disabled={!t.configured}>
                      {t.label}{!t.configured ? "（未配置）" : ""}
                    </option>
                  ))}
                </select>
                {currentTemplate && (
                  <>
                    <div className="grid grid-cols-3 gap-2">
                      {currentTemplate.variables.map((v) => (
                        <div key={v}>
                          <label className="text-xs text-muted-foreground">{VAR_LABELS[v] || v}</label>
                          <Input
                            value={smsVars[v] || ""}
                            onChange={(e) => setSmsVars({ ...smsVars, [v]: e.target.value })}
                            className="h-8 text-sm"
                          />
                        </div>
                      ))}
                    </div>
                    <div className="rounded-md bg-muted/50 border px-3 py-2 text-sm text-muted-foreground">
                      <p className="text-xs font-medium text-foreground mb-1">短信预览</p>
                      {renderSmsPreview()}
                    </div>
                  </>
                )}
                <div className="flex items-center gap-2">
                  <Input
                    placeholder="测试手机号（最多3个，逗号分隔）"
                    value={testPhones}
                    onChange={(e) => setTestPhones(e.target.value)}
                    className="h-8 text-sm flex-1"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleTestSms}
                    disabled={testLoading || !testPhones.trim() || !currentTemplate?.configured}
                    className="h-8 whitespace-nowrap"
                  >
                    {testLoading ? "发送中..." : "测试发送"}
                  </Button>
                </div>
                {testResult && (
                  <p className="text-xs text-muted-foreground">{testResult}</p>
                )}
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => handleBlast(["sms"])}
                    disabled={blastLoading || !currentTemplate?.configured}
                    className="h-8"
                  >
                    {blastLoading && blastChannels.includes("sms") && !blastChannels.includes("a2a") ? "发送中..." : "群发给所有已通过报名者"}
                  </Button>
                  {blastChannels.includes("sms") && !blastChannels.includes("a2a") && blastResult && (
                    <span className="text-xs text-muted-foreground">{blastResult}</span>
                  )}
                </div>
              </div>

              <hr />

              {/* Agent message blast */}
              <div className="space-y-2">
                <p className="text-sm font-medium">Agent 消息群发</p>
                <p className="text-xs text-muted-foreground">向所有已通过报名者的 Agent 发送自定义消息</p>
                <Textarea
                  placeholder="消息内容..."
                  rows={3}
                  value={blastContent}
                  onChange={(e) => setBlastContent(e.target.value)}
                />
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    onClick={() => handleBlast(["a2a"])}
                    disabled={blastLoading || !blastContent.trim()}
                    className="h-8"
                  >
                    {blastLoading && blastChannels.includes("a2a") ? "发送中..." : "发送 Agent 消息"}
                  </Button>
                  {blastChannels.includes("a2a") && !blastChannels.includes("sms") && blastResult && (
                    <span className="text-xs text-muted-foreground">{blastResult}</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>}

      {/* Co-Host Management */}
      {hasPerm("view_cohosts") && <div className="mb-6">
        {isHost ? (
          <>
            <button
              onClick={() => setShowCohosts(!showCohosts)}
              className="text-sm font-medium text-primary hover:underline"
            >
              {showCohosts ? "收起" : "展开"}联合主办方
              {cohosts.length > 0 && ` (${cohosts.length})`}
            </button>
            {showCohosts && (
              <Card className="mt-3">
                <CardContent className="p-4 space-y-3">
                  <div className="flex gap-2">
                    <Input
                      placeholder="输入联合主办方手机号"
                      value={newCohostPhone}
                      onChange={(e) => { setNewCohostPhone(e.target.value); setCohostError(""); }}
                      className="flex-1"
                    />
                    <Button size="sm" onClick={handleAddCohost} disabled={cohostLoading || !newCohostPhone.trim()}>
                      {cohostLoading ? "添加中..." : "添加"}
                    </Button>
                  </div>
                  {newCohostPhone.trim() && (
                    <PermissionCheckboxes
                      value={newCohostPerms}
                      onChange={setNewCohostPerms}
                    />
                  )}
                  {cohostError && <p className="text-xs text-destructive">{cohostError}</p>}
                  {cohosts.length === 0 ? (
                    <p className="text-sm text-muted-foreground">暂无联合主办方</p>
                  ) : (
                    <div className="space-y-2">
                      {cohosts.map((ch) => (
                        <div key={ch.id} className="rounded-lg bg-muted/50 p-2.5">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {ch.avatar_url ? (
                                <img src={ch.avatar_url} alt="" className="h-6 w-6 rounded-full" />
                              ) : (
                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs">
                                  {(ch.nickname || "?")[0]}
                                </span>
                              )}
                              <span className="text-sm font-medium">{ch.nickname}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-xs"
                                onClick={() => {
                                  if (editingCohostId === ch.id) {
                                    setEditingCohostId(null);
                                  } else {
                                    setEditingCohostId(ch.id);
                                    setEditingPerms((ch.permissions || []).filter((p: string) => p !== "checkin"));
                                  }
                                }}
                              >
                                {editingCohostId === ch.id ? "取消" : "权限"}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-xs text-destructive hover:text-destructive"
                                onClick={() => handleRemoveCohost(ch.id)}
                              >
                                移除
                              </Button>
                            </div>
                          </div>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {(ch.permissions || ["checkin"]).map((p: string) => (
                              <span key={p} className="inline-block rounded bg-background px-1.5 py-0.5 text-[11px] text-muted-foreground">
                                {PERM_LABELS[p] || p}
                              </span>
                            ))}
                          </div>
                          {editingCohostId === ch.id && (
                            <div className="mt-2 border-t pt-2">
                              <PermissionCheckboxes value={editingPerms} onChange={setEditingPerms} />
                              <Button
                                size="sm"
                                className="mt-2"
                                onClick={() => handleUpdateCohostPerms(ch.id, editingPerms)}
                              >
                                保存权限
                              </Button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </>
        ) : null}
      </div>}

      {/* Staff Management */}
      {hasPerm("view_staff") && <div className="mb-6">
        <button
          onClick={() => setShowStaff(!showStaff)}
          className="text-sm font-medium text-primary hover:underline"
        >
          {showStaff ? "收起" : "展开"} Staff Agent 管理
          {staffList.length > 0 && ` (${staffList.length})`}
        </button>
        {showStaff && (
          <Card className="mt-3">
            <CardContent className="p-4 space-y-3">
              {isHost && (
                <div className="flex gap-2">
                  <Input
                    placeholder="输入 Agent 名称（如 my-agent）"
                    value={newStaffName}
                    onChange={(e) => setNewStaffName(e.target.value)}
                    className="flex-1"
                  />
                  <Button size="sm" onClick={handleAddStaff} disabled={staffLoading || !newStaffName.trim()}>
                    {staffLoading ? "添加中..." : "添加 Staff"}
                  </Button>
                </div>
              )}
              {staffList.length === 0 ? (
                <p className="text-sm text-muted-foreground">暂无 Staff Agent</p>
              ) : (
                <div className="space-y-2">
                  {staffList.map((s) => (
                    <div key={s.id} className="flex items-center justify-between rounded-lg bg-muted/50 p-2.5">
                      <div>
                        <p className="text-sm font-medium">{s.agent_display_name || s.agent_name}</p>
                        <p className="text-xs text-muted-foreground">角色: {s.role}</p>
                      </div>
                      {isHost && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-xs text-destructive hover:text-destructive"
                          onClick={() => handleRemoveStaff(s.id)}
                        >
                          移除
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>}

      {/* Winners */}
      {hasPerm("view_winners") && <div className="mb-6">
        <button
          onClick={() => setShowWinners(!showWinners)}
          className="text-sm font-medium text-primary hover:underline"
        >
          {showWinners ? "收起" : "展开"}获奖者管理
          {winners.length > 0 && ` (${winners.length})`}
        </button>
        {showWinners && (
          <Card className="mt-3">
            <CardContent className="p-4">
              {winners.length === 0 ? (
                <p className="text-sm text-muted-foreground">暂无获奖者。可通过 Staff Agent API 评选获奖者。</p>
              ) : (
                <div className="space-y-2">
                  {winners.map((w) => (
                    <div key={w.id} className="flex items-center justify-between rounded-lg bg-muted/50 p-2.5">
                      <div className="flex items-center gap-3">
                        {w.rank && (
                          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                            #{w.rank}
                          </span>
                        )}
                        <div>
                          <p className="text-sm font-medium">{w.user?.nickname || w.agent?.name || "未知"}</p>
                          {w.prize_name && <p className="text-xs text-muted-foreground">{w.prize_name}</p>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>}

      {/* Post-event Feedback */}
      {isHost && event && event.status === "completed" && (
        <div className="mb-6">
          <button
            onClick={() => { setShowFeedback(!showFeedback); if (!showFeedback) loadFeedback(); }}
            className="text-sm font-medium text-primary hover:underline"
          >
            {showFeedback ? "收起" : "展开"}活动评价
            {feedbackData.count > 0 && ` (${feedbackData.count} 条, 均分 ${feedbackData.avg_rating})`}
          </button>
          {showFeedback && (
            <Card className="mt-3">
              <CardContent className="p-4">
                {feedbackData.items.length === 0 ? (
                  <p className="text-sm text-muted-foreground">暂无评价</p>
                ) : (
                  <div className="space-y-2">
                    {feedbackData.items.map((fb) => (
                      <div key={fb.id} className="rounded-lg bg-muted/50 p-2.5">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{fb.user?.nickname || "匿名"}</span>
                          <span className="text-xs text-amber-500">
                            {"★".repeat(fb.rating)}{"☆".repeat(5 - fb.rating)}
                          </span>
                        </div>
                        {fb.comment && <p className="mt-1 text-sm text-muted-foreground">{fb.comment}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Answer Statistics */}
      {hasPerm("view_stats") && answerStats.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => setShowStats(!showStats)}
            className="text-sm font-medium text-primary hover:underline"
          >
            {showStats ? "收起" : "展开"}问卷统计
          </button>
          {showStats && (
            <div className="mt-3 space-y-4">
              {answerStats.map((stat) => (
                <Card key={stat.question_id}>
                  <CardContent className="p-4">
                    <p className="text-sm font-medium">{stat.question_text}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {stat.total_answers} 人回答 ·
                      <span className="ml-1">
                        {{ text: "文本", select: "单选", multiselect: "多选" }[stat.question_type] || stat.question_type}
                      </span>
                    </p>
                    {Object.keys(stat.stats).length > 0 && (
                      <div className="mt-2 space-y-1.5">
                        {Object.entries(stat.stats)
                          .sort(([, a], [, b]) => b - a)
                          .map(([value, count]) => (
                            <div key={value} className="flex items-center gap-2">
                              <div className="flex-1">
                                <div className="flex items-center justify-between text-xs">
                                  <button
                                    onClick={() => filterByAnswer(stat.question_id, value)}
                                    className="text-foreground hover:text-primary hover:underline truncate max-w-[200px]"
                                    title={`筛选：${value}`}
                                  >
                                    {value}
                                  </button>
                                  <span className="text-muted-foreground ml-2 shrink-0">
                                    {count} ({stat.total_answers > 0 ? Math.round((count / stat.total_answers) * 100) : 0}%)
                                  </span>
                                </div>
                                <div className="mt-0.5 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                                  <div
                                    className="h-full rounded-full bg-primary transition-all"
                                    style={{ width: `${stat.total_answers > 0 ? (count / stat.total_answers) * 100 : 0}%` }}
                                  />
                                </div>
                              </div>
                            </div>
                          ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Registration Approval */}
      {hasPerm("view_registrations") && <div className="mb-6">
        <button
          onClick={() => setShowRegs(!showRegs)}
          className="text-sm font-medium text-primary hover:underline"
        >
          {showRegs ? "收起" : "展开"}报名审批
          {regs.length > 0 && ` (${regs.length})`}
        </button>
        {showRegs && (
          <div className="mt-3">
            {/* Batch actions */}
            {isHost && pendingCount > 0 && (
              <div className="mb-4 flex items-center gap-2 rounded-lg bg-muted/50 p-3">
                <p className="text-sm">{pendingCount} 个报名待审批</p>
                <Button size="sm" onClick={handleBatchApprove}>全部通过</Button>
              </div>
            )}

            {/* Answer filter indicator */}
            {answerFilter && (
              <div className="mb-3 flex items-center gap-2 rounded-lg bg-blue-50 dark:bg-blue-950/30 p-2.5 text-sm">
                <span>
                  筛选中：<span className="font-medium">{answerFilter.value}</span>
                </span>
                <button onClick={clearAnswerFilter} className="text-xs text-primary hover:underline ml-auto">
                  清除筛选
                </button>
              </div>
            )}

            <div className="flex gap-2 mb-4 flex-wrap">
              {["all", "pending", "approved", "declined", "waitlisted"].map((s) => (
                <button
                  key={s}
                  onClick={() => { setFilter(s); if (answerFilter) clearAnswerFilter(); }}
                  className={`rounded-full px-3 py-1 text-xs transition-colors ${
                    filter === s ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"
                  }`}
                >
                  {{ all: "全部", pending: "待审批", approved: "已通过", declined: "已拒绝", waitlisted: "候补" }[s]}
                  {statusCounts[s] > 0 && (
                    <span className={`ml-1 inline-flex items-center justify-center rounded-full px-1.5 min-w-[18px] text-[10px] font-medium ${
                      filter === s ? "bg-primary-foreground/20 text-primary-foreground" : "bg-background text-muted-foreground"
                    }`}>
                      {statusCounts[s]}
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="space-y-2">
              {filteredRegs.length === 0 ? (
                <p className="py-8 text-center text-muted-foreground">暂无报名</p>
              ) : (
                filteredRegs.map((reg) => (
                  <Card key={reg.id}>
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-sm truncate">
                              {reg.user?.nickname || "未知用户"}
                            </p>
                            {reg.agent && (
                              <Badge variant="outline" className="text-[10px]">
                                Agent: {reg.agent.name}
                              </Badge>
                            )}
                            <Badge variant={
                              reg.status === "approved" ? "default" :
                              reg.status === "pending" ? "secondary" :
                              "outline"
                            }>
                              {{ approved: "已通过", pending: "待审批", declined: "已拒绝", waitlisted: "候补", cancelled: "已取消" }[reg.status] || reg.status}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {reg.user?.phone || "无手机号"} · {new Date(reg.registered_at).toLocaleString("zh-CN")}
                            {reg.checked_in_at && " · 已签到"}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 ml-2">
                          {reg.custom_answers && Object.keys(reg.custom_answers).length > 0 && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-xs h-7 px-2"
                              onClick={() => setExpandedReg(expandedReg === reg.id ? null : reg.id)}
                            >
                              {expandedReg === reg.id ? "收起" : "问卷"}
                            </Button>
                          )}
                          {isHost && reg.status === "pending" && (
                            <>
                              <Button size="sm" onClick={() => handleApprove(reg.id)}>通过</Button>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => handleWaitlist(reg.id)}
                              >
                                候补
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => setConfirmDialog({ type: "decline", regId: reg.id })}
                              >
                                拒绝
                              </Button>
                            </>
                          )}
                          {reg.status === "approved" && !reg.checked_in_at && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleScanCheckin(reg.qr_code_token)}
                              disabled={scanLoading}
                            >
                              签到
                            </Button>
                          )}
                        </div>
                      </div>

                      {expandedReg === reg.id && reg.custom_answers && (
                        <div className="mt-2 pt-2 border-t space-y-1.5">
                          {Object.entries(reg.custom_answers).map(([qId, value]) => {
                            const qStat = answerStats.find((s) => s.question_id === qId);
                            const label = qStat?.question_text || qId;
                            const displayValue = Array.isArray(value) ? value.join(", ") : String(value);
                            return (
                              <div key={qId} className="text-xs">
                                <span className="text-muted-foreground">{label}：</span>
                                <span className="font-medium">{displayValue}</span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>
        )}
      </div>}

      {/* Confirm Dialog */}
      {confirmDialog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setConfirmDialog(null)}
        >
          <div
            className="w-full max-w-sm bg-background rounded-xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-5 py-4">
              <h3 className="font-semibold">
                {confirmDialog.type === "cancel" && "确认取消活动？"}
                {confirmDialog.type === "delete" && "确认删除活动？"}
                {confirmDialog.type === "decline" && "确认拒绝此报名？"}
                {confirmDialog.type === "offline" && "确认暂时下线此活动？"}
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                {confirmDialog.type === "cancel" && "取消后参与者将收到通知，此操作不可撤销。"}
                {confirmDialog.type === "delete" && "删除后所有报名、问卷数据将被永久清除。"}
                {confirmDialog.type === "decline" && "拒绝后该用户将无法签到。"}
                {confirmDialog.type === "offline" && "下线后活动将对外隐藏，修改完成后可随时重新上线。"}
              </p>
            </div>
            <div className="px-5 py-3 border-t flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setConfirmDialog(null)}>
                返回
              </Button>
              <Button
                variant="destructive"
                className="flex-1"
                disabled={!!actionLoading}
                onClick={() => {
                  if (confirmDialog.type === "cancel") handleCancel();
                  else if (confirmDialog.type === "delete") handleDelete();
                  else if (confirmDialog.type === "decline" && confirmDialog.regId) handleDecline(confirmDialog.regId);
                  else if (confirmDialog.type === "offline") handleOffline();
                }}
              >
                {actionLoading ? "处理中..." : "确认"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

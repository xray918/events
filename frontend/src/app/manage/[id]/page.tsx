"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useRequireAuth } from "@/hooks/use-require-auth";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

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

export default function ManagePage() {
  const { authenticated } = useRequireAuth();
  const params = useParams();
  const eventId = params.id as string;
  const [regs, setRegs] = useState<Registration[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [expandedReg, setExpandedReg] = useState<string | null>(null);
  const [answerStats, setAnswerStats] = useState<AnswerStat[]>([]);
  const [showStats, setShowStats] = useState(false);
  const [answerFilter, setAnswerFilter] = useState<{ questionId: string; value: string } | null>(null);

  async function loadData() {
    try {
      const regRes = await fetch(`${API}/api/v1/host/events/${eventId}/registrations?limit=200`, { credentials: "include" });
      const allRegs = await regRes.json();
      if (allRegs.data) setRegs(allRegs.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function loadStats() {
    try {
      const res = await fetch(`${API}/api/v1/host/events/${eventId}/answer-stats`, { credentials: "include" });
      const data = await res.json();
      if (data.data) setAnswerStats(data.data);
    } catch {
      // ignore
    }
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
    } catch {
      // ignore
    }
  }

  function clearAnswerFilter() {
    setAnswerFilter(null);
    loadData();
  }

  useEffect(() => {
    if (authenticated) {
      loadData();
      loadStats();
    }
  }, [eventId, authenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleApprove(regId: string) {
    await fetch(`${API}/api/v1/host/events/${eventId}/registrations/${regId}/approve`, {
      method: "POST",
      credentials: "include",
    });
    loadData();
  }

  async function handleDecline(regId: string) {
    await fetch(`${API}/api/v1/host/events/${eventId}/registrations/${regId}/decline`, {
      method: "POST",
      credentials: "include",
    });
    loadData();
  }

  async function handleBatchApprove() {
    await fetch(`${API}/api/v1/host/events/${eventId}/registrations/batch-approve`, {
      method: "POST",
      credentials: "include",
    });
    loadData();
  }

  async function handlePublish() {
    await fetch(`${API}/api/v1/events/${eventId}/publish`, {
      method: "POST",
      credentials: "include",
    });
    loadData();
  }

  const filteredRegs = filter === "all" ? regs : regs.filter((r) => r.status === filter);
  const pendingCount = regs.filter((r) => r.status === "pending").length;

  if (loading) {
    return <div className="mx-auto max-w-4xl px-4 py-10"><p className="text-muted-foreground">加载中...</p></div>;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">活动管理</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handlePublish}>发布活动</Button>
          <a href={`${API}/api/v1/host/events/${eventId}/registrations/export`} target="_blank" rel="noreferrer">
            <Button variant="outline">导出 CSV</Button>
          </a>
        </div>
      </div>

      {/* Stats */}
      <div className="mt-6 grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold">{regs.length}</p>
            <p className="text-xs text-muted-foreground">总报名</p>
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
            <p className="text-2xl font-bold">{regs.filter((r) => r.checked_in_at).length}</p>
            <p className="text-xs text-muted-foreground">已签到</p>
          </CardContent>
        </Card>
      </div>

      {/* Answer Statistics */}
      {answerStats.length > 0 && (
        <div className="mt-4">
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

      {/* Batch actions */}
      {pendingCount > 0 && (
        <div className="mt-4 flex items-center gap-2 rounded-lg bg-muted/50 p-3">
          <p className="text-sm">{pendingCount} 个报名待审批</p>
          <Button size="sm" onClick={handleBatchApprove}>全部通过</Button>
        </div>
      )}

      {/* Answer filter indicator */}
      {answerFilter && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-blue-50 dark:bg-blue-950/30 p-2.5 text-sm">
          <span>
            筛选中：<span className="font-medium">{answerFilter.value}</span>
          </span>
          <button onClick={clearAnswerFilter} className="text-xs text-primary hover:underline ml-auto">
            清除筛选
          </button>
        </div>
      )}

      {/* Registrations */}
      <div className="mt-6">
        <div className="flex gap-2 mb-4">
          {["all", "pending", "approved", "declined", "waitlisted"].map((s) => (
            <button
              key={s}
              onClick={() => { setFilter(s); if (answerFilter) clearAnswerFilter(); }}
              className={`rounded-full px-3 py-1 text-xs transition-colors ${
                filter === s ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"
              }`}
            >
              {{ all: "全部", pending: "待审批", approved: "已通过", declined: "已拒绝", waitlisted: "候补" }[s]}
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
                      {reg.status === "pending" && (
                        <>
                          <Button size="sm" onClick={() => handleApprove(reg.id)}>通过</Button>
                          <Button size="sm" variant="outline" onClick={() => handleDecline(reg.id)}>拒绝</Button>
                        </>
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
    </div>
  );
}

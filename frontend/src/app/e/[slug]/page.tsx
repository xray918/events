import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { fetchAPI, EventItem } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RegisterButton } from "@/components/register-button";
import { EventDescription } from "@/components/event-description";
import { HostActions } from "@/components/host-actions";
import { EventFeedback } from "@/components/event-feedback";
import { getCoverStyle, getThemeForEvent } from "@/lib/themes";

async function getEvent(slug: string): Promise<EventItem | null> {
  try {
    const res = await fetchAPI<{ success: boolean; data: EventItem }>(
      `/api/v1/events/${slug}`,
      { next: { revalidate: 10 } }
    );
    return res.data || null;
  } catch {
    return null;
  }
}

function formatFullDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

const typeLabels: Record<string, string> = {
  in_person: "线下活动",
  online: "线上活动",
  hybrid: "混合活动",
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://events.clawdchat.cn";

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const event = await getEvent(params.slug);
  if (!event) return { title: "活动不存在 — 虾聊活动" };

  // Build description: time + location
  const descParts: string[] = [];
  if (event.start_time) {
    const d = new Date(event.start_time);
    const datePart = d.toLocaleDateString("zh-CN", {
      month: "long", day: "numeric", weekday: "short",
    });
    const timePart = d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    descParts.push(`${datePart} ${timePart}`);
  }
  if (event.location_name) descParts.push(event.location_name);
  const description = descParts.join(" · ") || "虾聊 · Events";

  const eventUrl = `${SITE_URL}/e/${event.slug}`;
  // Use the generated poster as OG image — it contains cover, title and branding
  const ogImage = `${API_BASE}/api/v1/events/${event.slug}/poster`;

  return {
    title: `${event.title} — 虾聊活动`,
    description,
    openGraph: {
      title: event.title,
      description,
      url: eventUrl,
      siteName: "虾聊 · Events",
      locale: "zh_CN",
      type: "website",
      images: [{ url: ogImage, width: 750, alt: event.title }],
    },
    twitter: {
      card: "summary_large_image",
      title: event.title,
      description,
      images: [ogImage],
    },
  };
}

export default async function EventDetailPage({
  params,
}: {
  params: { slug: string };
}) {
  const event = await getEvent(params.slug);
  if (!event) return notFound();

  const hasCover = !!event.cover_image_url;
  const theme = getThemeForEvent(event);
  const coverStyle = getCoverStyle(event);
  const titleColor = hasCover ? "text-white" : theme.textColor === "white" ? "text-white" : "text-gray-900";
  const badgeBg = hasCover || theme.textColor === "white" ? "bg-white/20 text-white border-white/30" : "bg-black/10 text-gray-800 border-black/10";

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* Cover */}
      <div
        className="relative w-full aspect-video rounded-2xl overflow-hidden"
        style={coverStyle}
      >
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
        {/* 左上角 logo — 始终显示 */}
        <div className="absolute top-0 left-0 p-3">
          <div className="h-10 w-10 rounded-xl overflow-hidden opacity-90">
            <img src="/logo-center.png" alt="虾聊" className="h-full w-full scale-110" />
          </div>
        </div>
        {!hasCover && (
          <>
            {/* 无封面时标题居中显示 */}
            <div className="absolute inset-0 flex items-center justify-center p-8">
              <h1 className={`text-3xl font-bold drop-shadow sm:text-4xl text-center ${titleColor}`}>
                {event.title}
              </h1>
            </div>
            {/* 标签放右下角 */}
            <div className="absolute bottom-0 right-0 p-4 flex items-center gap-2">
              <Badge className={`${badgeBg} backdrop-blur-sm text-xs`}>
                {typeLabels[event.event_type] || event.event_type}
              </Badge>
              {event.require_approval && (
                <Badge className={`${badgeBg} backdrop-blur-sm text-xs`}>需审批</Badge>
              )}
            </div>
          </>
        )}
      </div>

      {/* Content */}
      <div className="mt-6 space-y-6">
        {/* Host Actions (only visible to event owner) */}
        <HostActions
          eventId={event.id}
          eventStatus={event.status}
          hostId={event.host?.id || ""}
          circleId={event.circle_id}
        />

        {/* Title & Meta — 有封面时显示在图片下方 */}
        {hasCover && (
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="outline" className="text-xs">
                {typeLabels[event.event_type] || event.event_type}
              </Badge>
              {event.require_approval && (
                <Badge variant="outline" className="text-xs">需审批</Badge>
              )}
            </div>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">{event.title}</h1>
          </div>
        )}

        {/* Date & Location Card */}
        <div className="rounded-xl border bg-card p-5 space-y-3">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-lg">
              📅
            </div>
            <div>
              <p className="font-medium">{formatFullDate(event.start_time)}</p>
              <p className="text-sm text-muted-foreground">
                {formatTime(event.start_time)}
                {event.end_time && ` — ${formatTime(event.end_time)}`}
              </p>
              {event.registration_deadline && (
                <p className="text-xs text-amber-600 mt-1">
                  报名截止：{formatFullDate(event.registration_deadline)} {formatTime(event.registration_deadline)}
                </p>
              )}
            </div>
          </div>

          {event.location_name && (
            <>
              <Separator />
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-lg">
                  📍
                </div>
                <div>
                  <p className="font-medium">{event.location_name}</p>
                  {event.location_address && (
                    <p className="text-sm text-muted-foreground">{event.location_address}</p>
                  )}
                  {event.address_masked && (
                    <p className="text-xs text-amber-600 mt-1">🔒 报名通过后查看完整地址</p>
                  )}
                </div>
              </div>
            </>
          )}

          {event.online_url && (
            <>
              <Separator />
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-lg">
                  🔗
                </div>
                <div>
                  <p className="font-medium">线上参会链接</p>
                  <p className="text-sm text-muted-foreground break-all">{event.online_url}</p>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Registration + Share */}
        <div className="rounded-xl border bg-card p-5 space-y-4">
          {/* Attendees preview */}
          {event.attendees_preview && event.attendees_preview.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">已报名</span>
              <div className="flex -space-x-2">
                {event.attendees_preview.slice(0, 8).map((a: { nickname: string; avatar_url: string | null }, i: number) => (
                  a.avatar_url ? (
                    <img key={i} src={a.avatar_url} alt="" className="h-7 w-7 rounded-full border-2 border-background" title={a.nickname} />
                  ) : (
                    <span key={i} className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted text-[10px]" title={a.nickname}>
                      {(a.nickname || "?")[0]}
                    </span>
                  )
                ))}
              </div>
              {(event.registration_count || 0) > 8 && (
                <span className="text-xs text-muted-foreground">
                  +{(event.registration_count || 0) - 8}
                </span>
              )}
            </div>
          )}

          {/* 报名状态/操作行（始终在卡片底部） */}
          <RegisterButton
            slug={event.slug}
            title={event.title}
            questions={event.custom_questions}
            eventStatus={event.status}
            registrationDeadline={event.registration_deadline}
            capacity={event.capacity}
            registrationLimit={event.registration_limit}
            registrationCount={event.registration_count}
          />
        </div>

        {/* Host & Co-Hosts */}
        {event.host && (
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm text-muted-foreground">主办</span>
            <div className="flex items-center gap-3 flex-wrap">
              {/* 主办方：优先显示 organizer_name，其次 host.nickname */}
              <div className="flex items-center gap-2">
                {event.host.avatar_url ? (
                  <img src={event.host.avatar_url} alt="" className="h-6 w-6 rounded-full" />
                ) : (
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs">
                    {(event.organizer_name || event.host.nickname || "?")[0]}
                  </span>
                )}
                <span className="text-sm font-medium">
                  {event.organizer_name || event.host.nickname}
                </span>
              </div>
              {/* 联合主办 */}
              {(event.cohosts || []).map((h: { id: string; nickname: string; avatar_url: string | null }, i: number) => (
                <div key={h.id || i} className="flex items-center gap-2">
                  {h.avatar_url ? (
                    <img src={h.avatar_url} alt="" className="h-6 w-6 rounded-full" />
                  ) : (
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs">
                      {(h.nickname || "?")[0]}
                    </span>
                  )}
                  <span className="text-sm font-medium">{h.nickname}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Description (Markdown) */}
        {event.description && (
          <div>
            <h2 className="text-lg font-semibold">活动详情</h2>
            <div className="mt-2">
              <EventDescription content={event.description} />
            </div>
          </div>
        )}

        {/* Post-event feedback (only for completed events) */}
        {event.status === "completed" && (
          <EventFeedback slug={event.slug} />
        )}

        {/* Custom Questions Preview */}
        {event.custom_questions && event.custom_questions.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold">报名信息</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              报名时需要填写以下信息：
            </p>
            <ul className="mt-2 space-y-1">
              {event.custom_questions.map((q) => (
                <li key={q.id} className="text-sm text-muted-foreground flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
                  {q.question_text}
                  {q.is_required && <span className="text-destructive text-xs">*</span>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

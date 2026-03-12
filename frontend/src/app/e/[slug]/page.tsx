import { notFound } from "next/navigation";
import { fetchAPI, EventItem } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RegisterButton } from "@/components/register-button";
import { EventDescription } from "@/components/event-description";
import { SharePosterButton } from "@/components/share-poster-button";
import { HostActions } from "@/components/host-actions";

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

const defaultCovers = [
  "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
  "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
  "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
  "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
  "linear-gradient(135deg, #fa709a 0%, #fee140 100%)",
  "linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)",
];

function getDefaultCover(id: string): string {
  const idx = parseInt(id.replace(/-/g, "").slice(0, 8), 16) % defaultCovers.length;
  return defaultCovers[idx];
}

export default async function EventDetailPage({
  params,
}: {
  params: { slug: string };
}) {
  const event = await getEvent(params.slug);
  if (!event) return notFound();

  const hasCover = !!event.cover_image_url;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* Cover Image */}
      <div
        className="relative h-56 w-full rounded-2xl overflow-hidden sm:h-72"
        style={
          hasCover
            ? { backgroundImage: `url(${event.cover_image_url})`, backgroundSize: "cover", backgroundPosition: "center" }
            : { background: getDefaultCover(event.id) }
        }
      >
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
      </div>

      {/* Content */}
      <div className="mt-6 space-y-6">
        {/* Host Actions (only visible to event owner) */}
        <HostActions
          eventId={event.id}
          eventStatus={event.status}
          hostId={event.host?.id || ""}
        />

        {/* Title & Meta */}
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
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">
                {event.registration_count || 0} 人已报名
                {event.capacity && ` · 限 ${event.capacity} 人`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <SharePosterButton slug={event.slug} title={event.title} />
              <RegisterButton slug={event.slug} questions={event.custom_questions} />
            </div>
          </div>
        </div>

        {/* Host */}
        {event.host && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">主办</span>
            <div className="flex items-center gap-2">
              {event.host.avatar_url ? (
                <img src={event.host.avatar_url} alt="" className="h-6 w-6 rounded-full" />
              ) : (
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs">
                  {(event.host.nickname || "?")[0]}
                </span>
              )}
              <span className="text-sm font-medium">{event.host.nickname}</span>
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

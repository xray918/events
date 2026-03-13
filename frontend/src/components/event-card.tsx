import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EventItem } from "@/lib/api";
import { getCoverStyle } from "@/lib/themes";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
    weekday: "short",
  });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

const typeLabels: Record<string, string> = {
  in_person: "线下",
  online: "线上",
  hybrid: "混合",
};

export function EventCard({ event }: { event: EventItem }) {
  return (
    <Link href={`/e/${event.slug}`}>
      <Card className="group overflow-hidden border-0 shadow-sm hover:shadow-lg transition-all duration-300 cursor-pointer">
        {/* Cover */}
        <div
          className="relative h-40 w-full"
          style={getCoverStyle(event)}
        >
          <div className="absolute inset-0 bg-black/10 group-hover:bg-black/5 transition-colors" />
          <div className="absolute top-3 left-3">
            <Badge variant="secondary" className="bg-white/90 text-xs font-medium backdrop-blur-sm">
              {typeLabels[event.event_type] || event.event_type}
            </Badge>
          </div>
        </div>

        <CardContent className="p-4">
          {/* Date */}
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            {formatDate(event.start_time)} · {formatTime(event.start_time)}
          </p>

          {/* Title */}
          <h3 className="mt-1.5 text-base font-semibold leading-snug line-clamp-2 group-hover:text-primary transition-colors">
            {event.title}
          </h3>

          {/* Location */}
          {event.location_name && (
            <p className="mt-2 text-xs text-muted-foreground line-clamp-1">
              {event.location_name}
            </p>
          )}

          {/* Bottom row */}
          <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
            {event.host && (
              <span className="flex items-center gap-1.5">
                {event.host.avatar_url ? (
                  <img src={event.host.avatar_url} alt="" className="h-4 w-4 rounded-full" />
                ) : (
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-muted text-[10px]">
                    {(event.host.nickname || "?")[0]}
                  </span>
                )}
                {event.host.nickname}
              </span>
            )}
            {event.registration_count != null && event.registration_count > 0 && (
              <span>{event.registration_count} 人报名</span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

import { fetchAPI, EventItem } from "@/lib/api";
import { EventCard } from "@/components/event-card";
import Link from "next/link";

async function getPastEvents(): Promise<{ data: EventItem[]; total: number }> {
  try {
    const res = await fetchAPI<{ success: boolean; data: EventItem[]; total: number }>(
      "/api/v1/events/past/list",
      { next: { revalidate: 60 } }
    );
    return { data: res.data || [], total: res.total || 0 };
  } catch {
    return { data: [], total: 0 };
  }
}

export default async function PastEventsPage() {
  const { data: events, total } = await getPastEvents();

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <section className="mb-8">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            ← 返回首页
          </Link>
        </div>
        <h1 className="mt-4 text-3xl font-bold tracking-tight">往期活动</h1>
        <p className="mt-2 text-muted-foreground">
          共 {total} 个已结束的活动
        </p>
      </section>

      {events.length > 0 ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {events.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-20">
          <p className="text-xl font-medium text-muted-foreground">暂无往期活动</p>
        </div>
      )}
    </div>
  );
}

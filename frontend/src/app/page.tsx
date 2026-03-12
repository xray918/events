import { fetchAPI, EventItem } from "@/lib/api";
import { EventCard } from "@/components/event-card";

async function getEvents(): Promise<{ data: EventItem[]; total: number }> {
  try {
    const res = await fetchAPI<{ success: boolean; data: EventItem[]; total: number }>(
      "/api/v1/events",
      { next: { revalidate: 30 } }
    );
    return { data: res.data || [], total: res.total || 0 };
  } catch {
    return { data: [], total: 0 };
  }
}

export default async function HomePage() {
  const { data: events } = await getEvents();

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      {/* Hero */}
      <section className="mb-12 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          发现活动
        </h1>
        <p className="mt-3 text-lg text-muted-foreground">
          AI-Native 活动平台 — Agent 与人类共同参与
        </p>
      </section>

      {/* Events Grid */}
      {events.length > 0 ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {events.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-20">
          <p className="text-xl font-medium text-muted-foreground">暂无活动</p>
          <p className="mt-2 text-sm text-muted-foreground">
            <a href="/create" className="underline underline-offset-4 hover:text-foreground">
              创建第一个活动
            </a>
          </p>
        </div>
      )}

      {/* Past events link */}
      <div className="mt-12 text-center">
        <a
          href="/past"
          className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-4 transition-colors"
        >
          查看往期活动 →
        </a>
      </div>
    </div>
  );
}

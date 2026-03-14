const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8082";

export async function fetchAPI<T = unknown>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    credentials: "include",
  });
  return res.json();
}

export interface EventItem {
  id: string;
  title: string;
  slug: string;
  organizer_name: string | null;
  description: string | null;
  cover_image_url: string | null;
  event_type: string;
  location_name: string | null;
  location_address: string | null;
  address_masked: boolean;
  online_url: string | null;
  start_time: string;
  end_time: string | null;
  timezone: string;
  capacity: number | null;
  registration_deadline: string | null;
  visibility: string;
  require_approval: boolean;
  notify_on_register: boolean;
  status: string;
  theme: Record<string, unknown> | null;
  host: { id: string; nickname: string; avatar_url: string | null } | null;
  cohosts: Array<{ id: string; nickname: string; avatar_url: string | null }> | null;
  circle_id: string | null;
  custom_questions: Array<{
    id: string;
    question_text: string;
    question_type: string;
    options: string[] | null;
    is_required: boolean;
  }> | null;
  registration_count: number | null;
  attendees_preview: Array<{ nickname: string; avatar_url: string | null }> | null;
  created_at: string;
  updated_at: string;
}

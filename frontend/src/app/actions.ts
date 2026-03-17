"use server";

import { revalidatePath } from "next/cache";

export async function revalidateEventPage(slug: string) {
  revalidatePath(`/e/${slug}`);
}

export async function revalidateEventList() {
  revalidatePath("/");
  revalidatePath("/past");
}

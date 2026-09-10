import "server-only";

import { RateLimitError } from "@/lib/jobs/errors";
import { getSupabaseAdmin } from "@/lib/supabase/admin";

const MAX_ACTIVE_JOBS = 3;

export async function assertJobRateLimit(userId: string) {
  const { count, error } = await getSupabaseAdmin()
    .from("jobs")
    .select("id", { count: "exact", head: true })
    .in("status", ["queued", "running"])
    .eq("input->>user_id", userId);

  if (error) {
    throw new Error(`Failed to check job rate limit: ${error.message}`);
  }
  if ((count ?? 0) >= MAX_ACTIVE_JOBS) {
    throw new RateLimitError();
  }
}

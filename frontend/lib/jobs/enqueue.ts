import "server-only";

import { jsonAccepted } from "@/lib/jobs/http";
import { assertJobRateLimit } from "@/lib/jobs/rate-limit";
import { enqueueJob } from "@/lib/jobs/store";
import type { JobKind } from "@/lib/types/jobs";

export async function enqueueUserJob(
  userId: string,
  kind: Extract<JobKind, "ingest" | "recipe">,
  payload: Record<string, unknown>,
) {
  await assertJobRateLimit(userId);
  const jobId = await enqueueJob(kind, { ...payload, user_id: userId });
  return jsonAccepted(jobId);
}

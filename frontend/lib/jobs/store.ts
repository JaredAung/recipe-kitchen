import "server-only";

import { getSupabaseAdmin } from "@/lib/supabase/admin";
import { sendJobId } from "@/lib/jobs/sqs";
import type { JobKind, JobState, JobStatus } from "@/lib/types/jobs";

const JOB_KINDS = new Set<JobKind>(["ingest", "recipe", "audio", "video"]);
const JOB_STATES = new Set<JobState>(["queued", "running", "succeeded", "failed"]);
const JOB_ID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function enqueueJob(
  kind: JobKind,
  payload: Record<string, unknown>,
): Promise<string> {
  const admin = getSupabaseAdmin();
  const { data, error } = await admin
    .from("jobs")
    .insert({ kind, status: "queued", input: payload })
    .select("id")
    .single();

  if (error || !data?.id) {
    throw new Error(`Failed to insert job: ${error?.message ?? "empty response"}`);
  }

  const jobId = String(data.id);
  try {
    await sendJobId(jobId);
  } catch {
    await admin.from("jobs").delete().eq("id", jobId);
    throw new Error("Failed to enqueue job");
  }
  return jobId;
}

export async function fetchJobStatus(jobId: string): Promise<JobStatus | null> {
  if (!JOB_ID.test(jobId)) {
    return null;
  }

  const { data, error } = await getSupabaseAdmin()
    .from("jobs")
    .select("*")
    .eq("id", jobId)
    .limit(1)
    .maybeSingle();

  if (error) {
    throw new Error(`Failed to fetch job: ${error.message}`);
  }
  if (!data || typeof data !== "object") {
    return null;
  }
  return asJobStatus(data as Record<string, unknown>);
}

function asJobStatus(row: Record<string, unknown>): JobStatus {
  const jobId = typeof row.id === "string" ? row.id : "";
  const kind = row.kind;
  const status = row.status;
  if (
    !jobId ||
    typeof kind !== "string" ||
    typeof status !== "string" ||
    !JOB_KINDS.has(kind as JobKind) ||
    !JOB_STATES.has(status as JobState)
  ) {
    throw new Error("Failed to fetch job: unexpected row");
  }

  return {
    job_id: jobId,
    kind: kind as JobKind,
    status: status as JobState,
    result: row.result ?? null,
    error: typeof row.error === "string" ? row.error : "",
  };
}

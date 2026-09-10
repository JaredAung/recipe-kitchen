import "server-only";

import { ApiError } from "@/lib/api/client";
import { fetchJobStatus } from "@/lib/jobs/store";
import type { JobStatus } from "@/lib/types/jobs";

export async function getJob<T = unknown>(jobId: string): Promise<JobStatus<T>> {
  const job = await fetchJobStatus(jobId);
  if (!job) {
    throw new ApiError(404, "Job not found");
  }
  return job as JobStatus<T>;
}

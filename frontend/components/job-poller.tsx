"use client";

import { useJobPoller } from "@/hooks/use-job-poller";

export function JobPoller({ jobId }: { jobId: string }) {
  useJobPoller(jobId);
  return null;
}

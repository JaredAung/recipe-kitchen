import { request } from "./client";
import type { AudioResult } from "../types/audio";
import type { IngestResult } from "../types/ingest";
import type { JobStatus } from "../types/jobs";
import type { RecipeResult } from "../types/recipe";
import type { VideoResult } from "../types/video";

const DEFAULT_POLL_MS = 2000;
const DEFAULT_TIMEOUT_MS = 180_000;

export class JobFailedError extends Error {
  constructor(readonly job: JobStatus) {
    super(job.error || "This job failed.");
    this.name = "JobFailedError";
  }
}

export class JobTimeoutError extends Error {
  constructor(readonly jobId: string) {
    super("This is taking too long. Try again in a moment.");
    this.name = "JobTimeoutError";
  }
}

export type WaitForJobOptions = {
  intervalMs?: number;
  timeoutMs?: number;
  signal?: AbortSignal;
};

export function getJob<T = unknown>(jobId: string, init?: RequestInit): Promise<JobStatus<T>> {
  return request(`/jobs/${encodeURIComponent(jobId)}`, { cache: "no-store", ...init });
}

export function getIngestJob(jobId: string, init?: RequestInit): Promise<JobStatus<IngestResult>> {
  return getJob<IngestResult>(jobId, init);
}

export function getRecipeJob(jobId: string, init?: RequestInit): Promise<JobStatus<RecipeResult>> {
  return getJob<RecipeResult>(jobId, init);
}

export function getAudioJob(jobId: string, init?: RequestInit): Promise<JobStatus<AudioResult>> {
  return getJob<AudioResult>(jobId, init);
}

export function getVideoJob(jobId: string, init?: RequestInit): Promise<JobStatus<VideoResult>> {
  return getJob<VideoResult>(jobId, init);
}

export async function waitForJob<T>(
  jobId: string,
  getter: (jobId: string, init?: RequestInit) => Promise<JobStatus<T>>,
  options: WaitForJobOptions = {},
): Promise<JobStatus<T>> {
  const intervalMs = options.intervalMs ?? DEFAULT_POLL_MS;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const started = Date.now();

  while (true) {
    throwIfAborted(options.signal);
    const job = await getter(jobId, { signal: options.signal });
    if (job.status === "succeeded") {
      if (job.result == null) {
        throw new Error("Job succeeded without a result.");
      }
      return job;
    }
    if (job.status === "failed") {
      throw new JobFailedError(job);
    }
    if (Date.now() - started >= timeoutMs) {
      throw new JobTimeoutError(jobId);
    }
    await sleep(intervalMs, options.signal);
  }
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    throw new DOMException("Aborted", "AbortError");
  }
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

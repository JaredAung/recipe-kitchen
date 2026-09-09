export type JobKind = "ingest" | "recipe" | "audio" | "video";
export type JobState = "queued" | "running" | "succeeded" | "failed";

export type JobAccepted = {
  job_id: string;
};

export type JobStatus<T = unknown> = {
  job_id: string;
  kind: JobKind;
  status: JobState;
  result: T | null;
  error: string;
};

import { request } from "./client";
import type { JobAccepted } from "../types/jobs";

export function ingestFacebook(url: string, init?: RequestInit): Promise<JobAccepted> {
  return request("/ingest", {
    method: "POST",
    body: JSON.stringify({ url }),
    ...init,
  });
}

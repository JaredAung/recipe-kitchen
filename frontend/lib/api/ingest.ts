import { withUserAuth } from "./auth";
import { request } from "./client";
import type { JobAccepted } from "../types/jobs";

export async function ingestFacebook(url: string, init?: RequestInit): Promise<JobAccepted> {
  return request("/ingest", {
    method: "POST",
    body: JSON.stringify({ url }),
    ...(await withUserAuth(init, "Log in to extract this reel.")),
  });
}

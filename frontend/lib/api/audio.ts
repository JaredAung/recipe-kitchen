import { request } from "./client";
import type { JobAccepted } from "../types/jobs";

export function transcribeAudio(file: File): Promise<JobAccepted> {
  const body = new FormData();
  body.append("file", file);
  return request("/audio", { method: "POST", body });
}

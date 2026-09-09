import { request } from "./client";
import type { JobAccepted } from "../types/jobs";

export function extractVideo(file: File): Promise<JobAccepted> {
  const body = new FormData();
  body.append("file", file);
  return request("/video", { method: "POST", body });
}

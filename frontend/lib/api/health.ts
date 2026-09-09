import { request } from "./client";
import type { CurrentUser, Health } from "../types/health";

export function getHealth(): Promise<Health> {
  return request("/health");
}

export function getMe(accessToken: string): Promise<CurrentUser> {
  return request("/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

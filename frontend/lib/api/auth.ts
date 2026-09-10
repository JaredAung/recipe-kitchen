import { getAccessToken } from "@/lib/auth/access-token";

import { ApiError } from "./client";

export async function withUserAuth(
  init: RequestInit | undefined,
  unauthorized: string,
): Promise<RequestInit> {
  const token = await getAccessToken();
  if (!token) {
    throw new ApiError(401, unauthorized);
  }

  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return { ...init, headers };
}

import { getAccessToken } from "@/lib/auth/access-token";

import { ApiError, request } from "./client";
import type { JobAccepted } from "../types/jobs";
import type { RecipeExtractRequest } from "../types/recipe";

export async function extractRecipe(
  body: RecipeExtractRequest,
  init?: RequestInit,
): Promise<JobAccepted> {
  const token = await getAccessToken();
  if (!token) {
    throw new ApiError(401, "Log in to save this card.");
  }

  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);

  return request("/recipe", {
    method: "POST",
    body: JSON.stringify(body),
    ...init,
    headers,
  });
}

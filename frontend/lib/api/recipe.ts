import { withUserAuth } from "./auth";
import { request } from "./client";
import type { JobAccepted } from "../types/jobs";
import type { RecipeExtractRequest } from "../types/recipe";

export async function extractRecipe(
  body: RecipeExtractRequest,
  init?: RequestInit,
): Promise<JobAccepted> {
  return request("/recipe", {
    method: "POST",
    body: JSON.stringify(body),
    ...(await withUserAuth(init, "Log in to save this card.")),
  });
}

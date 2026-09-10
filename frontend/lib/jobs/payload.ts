import "server-only";

import { FacebookUrlError, parseFacebookVideoUrl } from "@/lib/facebook/url";
import { EmptyRecipeError, ValidationError } from "@/lib/jobs/errors";
import type { RecipeExtractRequest } from "@/lib/types/recipe";

export async function readJsonObject(request: Request): Promise<Record<string, unknown>> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    throw new ValidationError(["body"], "Request body must be JSON");
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new ValidationError(["body"], "Request body must be an object");
  }
  return body as Record<string, unknown>;
}

export function ingestPayloadFromBody(body: Record<string, unknown>): { url: string } {
  if (!("url" in body) || body.url == null) {
    throw new ValidationError(["body", "url"], "Field required");
  }
  if (typeof body.url !== "string") {
    throw new ValidationError(["body", "url"], "URL must be a string");
  }
  try {
    return { url: parseFacebookVideoUrl(body.url) };
  } catch (error) {
    if (error instanceof FacebookUrlError) {
      throw new ValidationError(["body", "url"], error.message);
    }
    throw error;
  }
}

export function recipePayloadFromBody(body: Record<string, unknown>): RecipeExtractRequest {
  const caption = stringField(body, "caption");
  const subtitleText = stringField(body, "subtitle_text");
  const video = stringField(body, "video");
  if (!caption.trim() && !subtitleText.trim() && !video.trim()) {
    throw new EmptyRecipeError();
  }

  return {
    caption,
    subtitle_text: subtitleText,
    video,
    thumbnail: stringField(body, "thumbnail"),
    source_url: nullableStringField(body, "source_url"),
    original_filename: nullableStringField(body, "original_filename"),
  };
}

function stringField(body: Record<string, unknown>, key: string): string {
  if (!(key in body) || body[key] === undefined) {
    return "";
  }
  if (typeof body[key] !== "string") {
    throw new ValidationError(["body", key], `${key} must be a string`);
  }
  return body[key];
}

function nullableStringField(body: Record<string, unknown>, key: string): string | null {
  if (!(key in body) || body[key] === undefined || body[key] === null) {
    return null;
  }
  if (typeof body[key] !== "string") {
    throw new ValidationError(["body", key], `${key} must be a string`);
  }
  return body[key];
}

import "server-only";

import { ApiError } from "@/lib/api/client";
import { AuthRequiredError } from "@/lib/jobs/auth";
import { EmptyRecipeError, RateLimitError, ValidationError } from "@/lib/jobs/errors";

export function jsonDetail(status: number, detail: unknown) {
  return Response.json({ detail }, { status });
}

export function jsonValidationError(loc: Array<string | number>, msg: string) {
  return jsonDetail(422, [{ type: "value_error", loc, msg }]);
}

export function jsonAccepted(jobId: string) {
  return Response.json({ job_id: jobId }, { status: 202 });
}

export function jobRouteResponse(error: unknown): Response {
  if (error instanceof AuthRequiredError) {
    return jsonDetail(401, error.message);
  }
  if (error instanceof EmptyRecipeError) {
    return jsonDetail(400, error.message);
  }
  if (error instanceof RateLimitError) {
    return jsonDetail(429, error.message);
  }
  if (error instanceof ValidationError) {
    return jsonValidationError(error.loc, error.message);
  }
  if (error instanceof ApiError) {
    if (error.status >= 500) {
      console.error(error);
    }
    return jsonDetail(error.status, error.detail);
  }
  console.error(error);
  const message = error instanceof Error ? error.message : "Failed to enqueue job";
  return jsonDetail(502, message);
}

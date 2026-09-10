import { requireUserId } from "@/lib/jobs/auth";
import { enqueueUserJob } from "@/lib/jobs/enqueue";
import { jobRouteResponse } from "@/lib/jobs/http";
import { readJsonObject, recipePayloadFromBody } from "@/lib/jobs/payload";

export async function POST(request: Request) {
  try {
    const userId = await requireUserId(request);
    const payload = recipePayloadFromBody(await readJsonObject(request));
    return await enqueueUserJob(userId, "recipe", payload);
  } catch (error) {
    return jobRouteResponse(error);
  }
}

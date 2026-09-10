import { requireUserId } from "@/lib/jobs/auth";
import { enqueueUserJob } from "@/lib/jobs/enqueue";
import { jobRouteResponse } from "@/lib/jobs/http";
import { ingestPayloadFromBody, readJsonObject } from "@/lib/jobs/payload";

export async function POST(request: Request) {
  try {
    const payload = ingestPayloadFromBody(await readJsonObject(request));
    const userId = await requireUserId(request);
    return await enqueueUserJob(userId, "ingest", payload);
  } catch (error) {
    return jobRouteResponse(error);
  }
}

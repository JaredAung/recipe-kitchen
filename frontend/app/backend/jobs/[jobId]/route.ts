import { getJob } from "@/lib/jobs/get-job";
import { jobRouteResponse } from "@/lib/jobs/http";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ jobId: string }> },
) {
  try {
    const { jobId } = await context.params;
    const job = await getJob(jobId);
    return Response.json(job, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    return jobRouteResponse(error);
  }
}

import "server-only";

import { SQSClient, SendMessageCommand } from "@aws-sdk/client-sqs";

import { loadRootEnv } from "@/lib/utils/load-root-env";

loadRootEnv();

function queueUrl() {
  const url = process.env.SQS_QUEUE_URL?.trim() || process.env.sqs_queue_url?.trim();
  if (!url) {
    throw new Error("SQS_QUEUE_URL is missing");
  }
  return url;
}

function region() {
  return process.env.AWS_REGION?.trim() || process.env.aws_region?.trim() || "us-east-1";
}

export async function sendJobId(jobId: string) {
  const client = new SQSClient({ region: region() });
  await client.send(
    new SendMessageCommand({
      QueueUrl: queueUrl(),
      MessageBody: JSON.stringify({ job_id: jobId }),
    }),
  );
}

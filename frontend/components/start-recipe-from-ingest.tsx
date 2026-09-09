"use client";

import { JobStatusPanel, PasteAgainLink } from "@/components/job-status-panel";
import { useStartRecipeFromIngest } from "@/hooks/use-start-recipe-from-ingest";
import type { IngestResult } from "@/lib/types/ingest";

export function StartRecipeFromIngest({
  ingestJobId,
  ingest,
}: {
  ingestJobId: string;
  ingest: IngestResult;
}) {
  const { error } = useStartRecipeFromIngest(ingestJobId, ingest);

  if (error) {
    return (
      <JobStatusPanel title="Could not extract a recipe from this reel." body={error}>
        <PasteAgainLink />
      </JobStatusPanel>
    );
  }

  return (
    <JobStatusPanel
      title="Writing the card."
      body="This page updates when the extract finishes."
    >
      <PasteAgainLink />
    </JobStatusPanel>
  );
}

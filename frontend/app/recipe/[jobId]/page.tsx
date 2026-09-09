import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { cache } from "react";

import { CookCard } from "@/components/cook-card";
import { JobPoller } from "@/components/job-poller";
import { JobStatusPanel, PasteAgainLink } from "@/components/job-status-panel";
import { StartRecipeFromIngest } from "@/components/start-recipe-from-ingest";
import { ApiError } from "@/lib/api/client";
import { getJob } from "@/lib/api/jobs";
import { recipeTitle } from "@/lib/recipes";
import type { IngestResult } from "@/lib/types/ingest";
import type { JobStatus } from "@/lib/types/jobs";
import type { RecipeResult } from "@/lib/types/recipe";

const loadJob = cache(getJob);

function asIngest(job: JobStatus): JobStatus<IngestResult> {
  return job as JobStatus<IngestResult>;
}

function asRecipe(job: JobStatus): JobStatus<RecipeResult> {
  return job as JobStatus<RecipeResult>;
}

export async function generateMetadata({
  params,
}: PageProps<"/recipe/[jobId]">): Promise<Metadata> {
  const { jobId } = await params;
  try {
    const job = await loadJob(jobId);
    if (job.kind === "ingest" && (job.status === "queued" || job.status === "running")) {
      return { title: "Pulling the reel · Recipe Kitchen" };
    }
    if (job.kind === "ingest" && job.status === "succeeded") {
      return { title: "Writing the card · Recipe Kitchen" };
    }
    if (job.kind === "recipe" && job.status === "succeeded") {
      const recipe = asRecipe(job).result;
      if (recipe?.title) {
        return { title: `${recipeTitle(recipe.title)} · Recipe Kitchen` };
      }
    }
  } catch {
    // Fall through to the generic title.
  }
  return { title: "Recipe · Recipe Kitchen" };
}

export default async function RecipeJobPage({ params }: PageProps<"/recipe/[jobId]">) {
  const { jobId } = await params;
  let job;
  try {
    job = await loadJob(jobId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    return (
      <JobStatusPanel
        title="Could not load this extract."
        body="Paste the reel again, or check that this link is still valid."
      >
        <PasteAgainLink />
      </JobStatusPanel>
    );
  }

  if (job.kind === "ingest") {
    return <IngestJobView jobId={jobId} job={asIngest(job)} />;
  }

  if (job.kind !== "recipe") {
    return (
      <JobStatusPanel title="This is not a recipe card.">
        <PasteAgainLink />
      </JobStatusPanel>
    );
  }

  return <RecipeJobView jobId={jobId} job={asRecipe(job)} />;
}

function IngestJobView({ jobId, job }: { jobId: string; job: JobStatus<IngestResult> }) {
  if (job.status === "queued" || job.status === "running") {
    return (
      <JobStatusPanel
        title="Pulling the reel."
        body="This page updates when the scrape finishes."
      >
        <JobPoller jobId={jobId} />
        <PasteAgainLink />
      </JobStatusPanel>
    );
  }

  if (job.status === "failed") {
    return (
      <JobStatusPanel
        title="Could not pull this reel."
        body={job.error && job.error !== "pipeline_failed" ? job.error : undefined}
      >
        <PasteAgainLink />
      </JobStatusPanel>
    );
  }

  if (!job.result) {
    return (
      <JobStatusPanel title="This reel finished without media.">
        <PasteAgainLink />
      </JobStatusPanel>
    );
  }

  return <StartRecipeFromIngest ingestJobId={jobId} ingest={job.result} />;
}

function RecipeJobView({ jobId, job }: { jobId: string; job: JobStatus<RecipeResult> }) {
  if (job.status === "queued" || job.status === "running") {
    return (
      <JobStatusPanel
        title="Writing the card."
        body="This page updates when the extract finishes."
      >
        <JobPoller jobId={jobId} />
        <PasteAgainLink />
      </JobStatusPanel>
    );
  }

  if (job.status === "failed") {
    return (
      <JobStatusPanel
        title="Could not extract a recipe from this reel."
        body={job.error && job.error !== "pipeline_failed" ? job.error : undefined}
      >
        <PasteAgainLink />
      </JobStatusPanel>
    );
  }

  const recipe = job.result;
  if (!recipe) {
    return (
      <JobStatusPanel title="This extract finished without a card.">
        <PasteAgainLink />
      </JobStatusPanel>
    );
  }

  return (
    <main className="flex-1 px-5 py-12 sm:px-8 sm:py-16">
      <div className="mx-auto w-full max-w-xl">
        <PasteAgainLink />
        <div className="mt-6">
          <CookCard
            titleAs="h1"
            title={recipeTitle(recipe.title)}
            totalTimeMinutes={recipe.total_time_minutes}
            ingredients={recipe.ingredients}
            steps={recipe.steps}
          />
        </div>
      </div>
    </main>
  );
}

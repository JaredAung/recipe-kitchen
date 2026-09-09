"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api/client";
import { extractRecipe } from "@/lib/api/recipe";
import { ingestHasExtractableMedia, recipeRequestFromIngest } from "@/lib/api/reel";
import { getAccessToken } from "@/lib/auth/access-token";
import type { IngestResult } from "@/lib/types/ingest";

const recipeJobKey = (ingestJobId: string) => `recipe-kitchen:ingest:${ingestJobId}:recipeJobId`;

const inflight = new Map<string, Promise<string>>();

function storedRecipeJobId(ingestJobId: string): string | null {
  if (typeof sessionStorage === "undefined") {
    return null;
  }
  return sessionStorage.getItem(recipeJobKey(ingestJobId));
}

function rememberRecipeJobId(ingestJobId: string, recipeJobId: string) {
  sessionStorage.setItem(recipeJobKey(ingestJobId), recipeJobId);
}

function startRecipeJob(ingestJobId: string, ingest: IngestResult): Promise<string> {
  const stored = storedRecipeJobId(ingestJobId);
  if (stored) {
    return Promise.resolve(stored);
  }
  const pending = inflight.get(ingestJobId);
  if (pending) {
    return pending;
  }
  const request = extractRecipe(recipeRequestFromIngest(ingest, ingest.media.source_url))
    .then((accepted) => {
      rememberRecipeJobId(ingestJobId, accepted.job_id);
      return accepted.job_id;
    })
    .finally(() => {
      inflight.delete(ingestJobId);
    });
  inflight.set(ingestJobId, request);
  return request;
}

function messageForError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.detail;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Could not start writing this card.";
}

export function useStartRecipeFromIngest(ingestJobId: string, ingest: IngestResult) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const emptyMedia = !ingestHasExtractableMedia(ingest);

  useEffect(() => {
    if (emptyMedia) {
      return;
    }

    const stored = storedRecipeJobId(ingestJobId);
    if (stored) {
      router.replace(`/recipe/${stored}`);
      return;
    }

    let cancelled = false;
    void (async () => {
      const token = await getAccessToken();
      if (!token) {
        if (!cancelled) {
          router.replace(`/login?next=${encodeURIComponent(`/recipe/${ingestJobId}`)}`);
        }
        return;
      }

      try {
        const recipeJobId = await startRecipeJob(ingestJobId, ingest);
        if (!cancelled) {
          router.replace(`/recipe/${recipeJobId}`);
        }
      } catch (caught: unknown) {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiError && (caught.status === 401 || caught.status === 403)) {
          router.replace(`/login?next=${encodeURIComponent(`/recipe/${ingestJobId}`)}`);
          return;
        }
        setError(messageForError(caught));
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [emptyMedia, ingest, ingestJobId, router]);

  return {
    error: emptyMedia
      ? "This reel did not include a caption, subtitles, or video."
      : error,
  };
}

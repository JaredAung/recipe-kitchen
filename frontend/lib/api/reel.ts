import type { IngestResult } from "../types/ingest";
import type { RecipeExtractRequest } from "../types/recipe";

export function ingestHasExtractableMedia(ingest: IngestResult): boolean {
  return Boolean(
    ingest.media.caption.trim() || ingest.subtitle_text.trim() || ingest.video.trim(),
  );
}

export function recipeRequestFromIngest(
  ingest: IngestResult,
  fallbackUrl: string,
): RecipeExtractRequest {
  return {
    caption: ingest.media.caption,
    subtitle_text: ingest.subtitle_text,
    video: ingest.video,
    thumbnail: ingest.thumbnail,
    source_url: ingest.media.source_url || fallbackUrl,
  };
}

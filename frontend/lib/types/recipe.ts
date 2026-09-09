import type { Ingredient } from "./ingredient";
import type { Step } from "./step";

export type StoppedAfter = "caption" | "subtitle" | "audio" | "visual";

export type RecipeExtractRequest = {
  caption?: string;
  subtitle_text?: string;
  video?: string;
  thumbnail?: string;
  source_url?: string | null;
  original_filename?: string | null;
};

export type ValidationIssue = {
  code: "ungrounded_evidence" | "generic_name";
  severity: "warning";
  detail: string;
  name: string;
  source: string;
  evidence: string;
};

export type RecipeResult = {
  id: string;
  stopped_after: StoppedAfter;
  sufficient: boolean;
  reason: string;
  title: string;
  cuisine: string;
  description: string;
  tags: string[];
  total_time_minutes: number | null;
  validation_issues: ValidationIssue[];
  validation_confidence: number | null;
  transcript_my: string | null;
  transcript_en: string;
  ingredients: Ingredient[];
  steps: Step[];
  caption_text: string;
};

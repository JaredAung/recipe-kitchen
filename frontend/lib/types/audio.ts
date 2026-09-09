import type { Ingredient } from "./ingredient";
import type { Step } from "./step";

export type AudioResult = {
  id: string;
  transcript_my: string | null;
  transcript_en: string;
  ingredients: Ingredient[];
  steps: Step[];
};

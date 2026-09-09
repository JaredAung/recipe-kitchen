import type { Ingredient } from "./ingredient";
import type { Step } from "./step";

export type VideoResult = {
  id: string;
  ingredients: Ingredient[];
  steps: Step[];
  confidence: number | null;
  usage: Record<string, unknown>;
};

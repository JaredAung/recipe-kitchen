export type CollectorSource = "audio" | "caption" | "visual";

export type Ingredient = {
  name: string;
  amount: string;
  evidence: string;
  source: CollectorSource;
  confidence: number | null;
};

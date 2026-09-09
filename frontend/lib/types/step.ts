import type { CollectorSource } from "./ingredient";

export type Step = {
  order: number;
  instruction: string;
  evidence: string;
  source: CollectorSource;
  confidence: number | null;
};

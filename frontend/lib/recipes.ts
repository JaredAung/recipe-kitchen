import { cache } from "react";

import { createClient } from "@/lib/supabase/server";

export type RecipeListItem = {
  id: string;
  title: string | null;
  cuisine: string;
  total_time_minutes: number | null;
  created_at: string;
};

type IngredientRow = {
  name: string;
  amount: string;
  evidence: string;
  source: string;
  sort_order: number;
};

type StepRow = {
  step_order: number;
  instruction: string;
  evidence: string;
  source: string;
};

export type SavedRecipe = {
  id: string;
  title: string | null;
  cuisine: string;
  total_time_minutes: number | null;
  source_url: string | null;
  ingredients: IngredientRow[];
  steps: StepRow[];
};

function asList(value: unknown): RecipeListItem[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((row): row is RecipeListItem => {
    return Boolean(row && typeof row === "object" && "id" in row && typeof row.id === "string");
  });
}

export const getSessionUserId = cache(async (): Promise<string | null> => {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const userId = data?.claims?.sub;
  return typeof userId === "string" ? userId : null;
});

export const listOwnRecipes = cache(async (): Promise<RecipeListItem[]> => {
  const userId = await getSessionUserId();
  if (!userId) {
    return [];
  }

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("recipes")
    .select("id, title, cuisine, total_time_minutes, created_at")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });

  if (error) {
    throw new Error(error.message);
  }

  return asList(data);
});

export const getOwnRecipe = cache(async (id: string): Promise<SavedRecipe | null> => {
  const userId = await getSessionUserId();
  if (!userId) {
    return null;
  }

  const supabase = await createClient();
  const { data, error } = await supabase
    .from("recipes")
    .select(
      "id, title, cuisine, total_time_minutes, source_url, recipe_ingredients(name, amount, evidence, source, sort_order), recipe_steps(step_order, instruction, evidence, source)",
    )
    .eq("id", id)
    .eq("user_id", userId)
    .maybeSingle();

  if (error) {
    throw new Error(error.message);
  }
  if (!data) {
    return null;
  }

  const ingredients = Array.isArray(data.recipe_ingredients)
    ? [...data.recipe_ingredients].sort(
        (left: IngredientRow, right: IngredientRow) => left.sort_order - right.sort_order,
      )
    : [];
  const steps = Array.isArray(data.recipe_steps)
    ? [...data.recipe_steps].sort(
        (left: StepRow, right: StepRow) => left.step_order - right.step_order,
      )
    : [];

  return {
    id: data.id,
    title: data.title,
    cuisine: data.cuisine,
    total_time_minutes: data.total_time_minutes,
    source_url: data.source_url,
    ingredients,
    steps,
  };
});

export function recipeTitle(title: string | null): string {
  const trimmed = title?.trim();
  return trimmed ? trimmed : "Untitled recipe";
}

import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { SourceChip } from "@/components/source-chip";
import { getOwnRecipe, getSessionUserId, recipeTitle } from "@/lib/recipes";

type Source = "audio" | "caption" | "visual";

function asSource(value: string): Source | null {
  if (value === "audio" || value === "caption" || value === "visual") {
    return value;
  }
  return null;
}

export async function generateMetadata({
  params,
}: PageProps<"/recipes/[id]">): Promise<Metadata> {
  const { id } = await params;
  const recipe = await getOwnRecipe(id);
  return {
    title: recipe ? `${recipeTitle(recipe.title)} · Recipe Kitchen` : "Recipe · Recipe Kitchen",
  };
}

export default async function RecipePage({ params }: PageProps<"/recipes/[id]">) {
  const { id } = await params;
  const userId = await getSessionUserId();

  if (!userId) {
    redirect(`/login?next=${encodeURIComponent(`/recipes/${id}`)}`);
  }

  const recipe = await getOwnRecipe(id);
  if (!recipe) {
    notFound();
  }

  const title = recipeTitle(recipe.title);

  return (
    <main className="flex-1 px-5 py-12 sm:px-8 sm:py-16">
      <div className="mx-auto w-full max-w-xl">
        <Link
          href="/recipes"
          className="font-display text-lg font-medium text-cast-iron underline-offset-4 hover:underline sm:text-xl"
        >
          My recipes
        </Link>

        <article className="mt-6 bg-phone-glow px-6 py-8 sm:px-10 sm:py-10">
          <div className="flex items-end justify-between gap-4 border-b border-turmeric pb-4">
            <h1 className="max-w-[16ch] font-body text-3xl leading-tight sm:text-4xl">{title}</h1>
            {recipe.total_time_minutes != null ? (
              <p className="shrink-0 pb-1 font-display text-sm text-steam">
                {recipe.total_time_minutes} min
              </p>
            ) : null}
          </div>

          <div className="mt-8 space-y-8">
            <div>
              <h2 className="font-display text-base font-semibold">Ingredients</h2>
              {recipe.ingredients.length === 0 ? (
                <p className="mt-4 text-cast-iron/85">No ingredients on this card.</p>
              ) : (
                <ul className="mt-4 divide-y divide-steam/30">
                  {recipe.ingredients.map((item, index) => {
                    const source = asSource(item.source);
                    return (
                      <li
                        key={`${item.name}-${index}`}
                        className="flex items-baseline justify-between gap-4 py-2.5"
                      >
                        <span>
                          {item.name}
                          {item.amount ? <span className="text-steam"> {item.amount}</span> : null}
                        </span>
                        {source ? <SourceChip source={source} /> : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div>
              <h2 className="font-display text-base font-semibold">Steps</h2>
              {recipe.steps.length === 0 ? (
                <p className="mt-4 text-cast-iron/85">No steps on this card.</p>
              ) : (
                <ol className="mt-4 space-y-4">
                  {recipe.steps.map((step) => {
                    const source = asSource(step.source);
                    return (
                      <li
                        key={`${step.step_order}-${step.instruction}`}
                        className="grid grid-cols-[1.5rem_1fr_auto] items-start gap-3"
                      >
                        <span className="font-display text-steam">{step.step_order}</span>
                        <p className="leading-7">{step.instruction}</p>
                        {source ? <SourceChip source={source} /> : null}
                      </li>
                    );
                  })}
                </ol>
              )}
            </div>
          </div>
        </article>
      </div>
    </main>
  );
}

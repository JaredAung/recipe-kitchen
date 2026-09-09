import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { getSessionUserId, listOwnRecipes, recipeTitle } from "@/lib/recipes";

export const metadata: Metadata = {
  title: "My recipes · Recipe Kitchen",
};

export default async function RecipesPage() {
  const userId = await getSessionUserId();

  if (!userId) {
    redirect(`/login?next=${encodeURIComponent("/recipes")}`);
  }

  const recipes = await listOwnRecipes();

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-5 py-12 sm:px-8 sm:py-16">
      <h1 className="font-display text-4xl font-semibold tracking-tight sm:text-5xl">
        My recipes
      </h1>
      <p className="mt-4 max-w-[40ch] text-lg leading-8 text-cast-iron/85">
        Cards pulled from the reels you pasted.
      </p>

      {recipes.length === 0 ? (
        <div className="mt-12 max-w-xl bg-phone-glow px-6 py-8 sm:px-10">
          <p className="text-lg leading-8">No cards on this stove yet.</p>
          <Link
            href="/#paste"
            className="mt-6 inline-flex min-h-12 items-center bg-turmeric px-4 font-display text-lg font-semibold text-cast-iron"
          >
            Paste a reel
          </Link>
        </div>
      ) : (
        <ul className="mt-12 divide-y divide-steam/30 border-y border-steam/30">
          {recipes.map((recipe) => (
            <li key={recipe.id}>
              <Link
                href={`/recipes/${recipe.id}`}
                className="flex items-baseline justify-between gap-4 py-5 hover:bg-phone-glow/70"
              >
                <span className="min-w-0">
                  <span className="block font-body text-2xl leading-tight sm:text-3xl">
                    {recipeTitle(recipe.title)}
                  </span>
                  {recipe.cuisine ? (
                    <span className="mt-1 block font-display text-base text-steam">
                      {recipe.cuisine}
                    </span>
                  ) : null}
                </span>
                {recipe.total_time_minutes != null ? (
                  <span className="shrink-0 font-display text-base text-steam">
                    {recipe.total_time_minutes} min
                  </span>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

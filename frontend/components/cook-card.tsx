import type { ReactNode } from "react";

import { SourceChip } from "@/components/source-chip";
import type { CollectorSource } from "@/lib/types/ingredient";

export type CookCardIngredient = {
  name: string;
  amount?: string;
  source: CollectorSource;
};

export type CookCardStep = {
  order: number;
  instruction: string;
  source: CollectorSource;
};

type CookCardProps = {
  eyebrow?: string;
  title: string;
  titleAs?: "h1" | "h2";
  totalTimeMinutes?: number | null;
  ingredients: CookCardIngredient[];
  steps: CookCardStep[];
  footer?: ReactNode;
};

export function CookCard({
  eyebrow,
  title,
  titleAs: TitleTag = "h2",
  totalTimeMinutes,
  ingredients = [],
  steps = [],
  footer,
}: CookCardProps) {
  return (
    <article className="mx-auto w-full max-w-xl bg-phone-glow px-6 py-8 sm:px-10 sm:py-10">
      {eyebrow ? <p className="font-display text-sm text-steam">{eyebrow}</p> : null}
      <div
        className={`flex items-end justify-between gap-4 border-b border-turmeric pb-4 ${eyebrow ? "mt-3" : ""}`}
      >
        <TitleTag className="max-w-[16ch] font-body text-3xl leading-tight sm:text-4xl">
          {title}
        </TitleTag>
        {totalTimeMinutes != null ? (
          <p className="shrink-0 pb-1 font-display text-sm text-steam">{totalTimeMinutes} min</p>
        ) : null}
      </div>

      <div className="mt-8 space-y-8">
        <div>
          <h3 className="font-display text-base font-semibold">Ingredients</h3>
          {ingredients.length === 0 ? (
            <p className="mt-4 text-cast-iron/85">No ingredients on this card.</p>
          ) : (
            <ul className="mt-4 divide-y divide-steam/30">
              {ingredients.map((item, index) => (
                <li
                  key={`${item.name}-${index}`}
                  className="flex items-baseline justify-between gap-4 py-2.5"
                >
                  <span>
                    {item.name}
                    {item.amount ? <span className="text-steam"> {item.amount}</span> : null}
                  </span>
                  <SourceChip source={item.source} />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h3 className="font-display text-base font-semibold">Steps</h3>
          {steps.length === 0 ? (
            <p className="mt-4 text-cast-iron/85">No steps on this card.</p>
          ) : (
            <ol className="mt-4 space-y-4">
              {steps.map((step) => (
                <li
                  key={`${step.order}-${step.instruction}`}
                  className="grid grid-cols-[1.5rem_1fr_auto] items-start gap-3"
                >
                  <span className="font-display text-steam">{step.order}</span>
                  <p className="leading-7">{step.instruction}</p>
                  <SourceChip source={step.source} />
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>

      {footer}
    </article>
  );
}

import Link from "next/link";

import { CookCard } from "@/components/cook-card";
import { PasteTicket } from "@/components/paste-ticket";
import { ReelFrame } from "@/components/reel-frame";

const sampleIngredients = [
  { name: "Wheat noodles", amount: "200g", source: "caption" as const },
  { name: "Garlic", amount: "4 cloves", source: "audio" as const },
  { name: "Ripe tomatoes", amount: "2", source: "visual" as const },
  { name: "Chili flakes", amount: "1 tsp", source: "audio" as const },
];

const sampleSteps = [
  { order: 1, instruction: "Boil the noodles until just tender, then drain.", source: "caption" as const },
  { order: 2, instruction: "Fry the garlic in oil until it smells sweet, not brown.", source: "audio" as const },
  { order: 3, instruction: "Crush in the tomatoes and cook down to a thick sauce.", source: "visual" as const },
  { order: 4, instruction: "Toss the noodles through. Finish with chili flakes.", source: "audio" as const },
];

export default function Home() {
  return (
    <main className="flex-1">
      <section className="mx-auto grid w-full max-w-6xl gap-12 px-5 py-12 sm:px-8 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] lg:items-center lg:gap-20 lg:py-20">
        <div className="px-4 py-8 sm:px-8">
          <ReelFrame />
        </div>
        <div className="max-w-2xl">
          <h1 className="font-display text-4xl font-semibold leading-[1.05] tracking-tight text-cast-iron sm:text-6xl">
            Paste the reel. Cook from the card.
          </h1>
          <p className="mt-5 max-w-[38ch] text-lg leading-8 text-cast-iron/85">
            A twenty-second video is a terrible recipe. Recipe Kitchen watches,
            listens, and reads the reel, then hands you ingredients and steps.
            Works for video recipes in Burmese, English.
          </p>
          <div className="mt-8">
            <PasteTicket />
          </div>
        </div>
      </section>

      <section className="border-y border-steam/40">
        <div className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-14 sm:px-8 md:grid-cols-3">
          <article>
            <h2 className="font-display text-xl font-semibold text-cast-iron">Listens</h2>
            <p className="mt-2 max-w-[36ch] leading-7 text-cast-iron/85">
              Speech from the reel, including Burmese, becomes amounts and
              steps you can follow without replaying.
            </p>
          </article>
          <article>
            <h2 className="font-display text-xl font-semibold text-cast-iron">Reads captions</h2>
            <p className="mt-2 max-w-[36ch] leading-7 text-cast-iron/85">
              On-screen text is pulled into the same card, so a flashed
              ingredient list is not lost.
            </p>
          </article>
          <article>
            <h2 className="font-display text-xl font-semibold text-cast-iron">Watches frames</h2>
            <p className="mt-2 max-w-[36ch] leading-7 text-cast-iron/85">
              What appears in the pan is checked against what was said, then
              merged into one recipe.
            </p>
          </article>
        </div>
      </section>

      <section className="px-5 py-16 sm:px-8">
        <CookCard
          eyebrow="The card, after the reel"
          title="Tomato garlic noodles"
          totalTimeMinutes={18}
          ingredients={sampleIngredients}
          steps={sampleSteps}
          footer={
            <Link
              href="#paste"
              className="mt-10 flex min-h-14 items-center justify-center bg-turmeric font-display text-lg font-semibold text-cast-iron"
            >
              Cook this
            </Link>
          }
        />
      </section>
    </main>
  );
}

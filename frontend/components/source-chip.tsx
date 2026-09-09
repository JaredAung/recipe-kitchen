type Source = "audio" | "caption" | "visual";

const chipLabel: Record<Source, string> = {
  audio: "audio",
  caption: "caption",
  visual: "visual",
};

export function SourceChip({ source }: { source: Source }) {
  return (
    <span className="inline-flex items-center border border-steam px-2 py-0.5 font-display text-xs tracking-[0.04em] text-steam">
      {chipLabel[source]}
    </span>
  );
}

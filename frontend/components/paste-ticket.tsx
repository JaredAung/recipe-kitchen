"use client";

import { usePasteReel } from "@/hooks/use-paste-reel";

export function PasteTicket() {
  const { url, onUrlChange, onSubmit, error, busy } = usePasteReel();
  const status = error ?? (busy ? "Pulling the reel…" : null);

  return (
    <form id="paste" onSubmit={onSubmit} className="relative w-full max-w-xl">
      <label htmlFor="reel-url" className="block font-display text-sm text-cast-iron">
        Facebook reel URL
      </label>
      <input
        id="reel-url"
        name="url"
        type="url"
        inputMode="url"
        autoComplete="url"
        placeholder="https://www.facebook.com/reel/…"
        value={url}
        disabled={busy}
        onChange={(event) => onUrlChange(event.target.value)}
        className="mt-2 min-h-12 w-full rounded-none border border-cast-iron bg-phone-glow px-3 font-mono text-[0.95rem] text-cast-iron placeholder:text-steam disabled:opacity-60"
      />
      <button
        type="submit"
        disabled={busy}
        className="mt-4 inline-flex min-h-12 w-full items-center justify-center bg-turmeric px-4 font-display text-base font-semibold text-cast-iron disabled:opacity-60 sm:w-auto sm:px-6"
      >
        {busy ? "Pulling the reel…" : "Paste a reel"}
      </button>
      <p
        role={error ? "alert" : "status"}
        aria-live="polite"
        className={`mt-3 min-h-6 text-sm ${error ? "text-chili" : "text-steam"}`}
      >
        {status}
      </p>
    </form>
  );
}

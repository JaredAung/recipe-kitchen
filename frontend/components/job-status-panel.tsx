import Link from "next/link";
import type { ReactNode } from "react";

export function PasteAgainLink() {
  return (
    <Link
      href="/#paste"
      className="font-display text-lg font-medium text-cast-iron underline-offset-4 hover:underline sm:text-xl"
    >
      Paste another reel
    </Link>
  );
}

export function JobStatusPanel({
  title,
  body,
  children,
}: {
  title: string;
  body?: string;
  children?: ReactNode;
}) {
  return (
    <main className="flex-1 px-5 py-12 sm:px-8 sm:py-16">
      <div className="mx-auto w-full max-w-xl bg-phone-glow px-6 py-8 sm:px-10 sm:py-10">
        <h1 className="font-body text-3xl leading-tight sm:text-4xl">{title}</h1>
        {body ? <p className="mt-4 text-lg leading-8 text-cast-iron/85">{body}</p> : null}
        <div className="mt-6">{children}</div>
      </div>
    </main>
  );
}

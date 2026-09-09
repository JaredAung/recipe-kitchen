import Link from "next/link";

import { signOut } from "@/lib/auth/actions";
import { createClient } from "@/lib/supabase/server";

export async function SiteHeader() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const email = typeof data?.claims?.email === "string" ? data.claims.email : null;

  return (
    <header className="border-b border-steam/40 bg-soapstone">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-8">
        <Link
          href="/"
          className="font-display text-2xl font-semibold tracking-[0.06em] text-cast-iron sm:text-3xl"
        >
          recipe kitchen
        </Link>
        <nav aria-label="Main" className="flex items-center gap-4 sm:gap-8">
          <Link
            href="/#paste"
            className="inline-flex min-h-12 items-center bg-turmeric px-4 py-2 font-display text-lg font-semibold text-cast-iron sm:text-xl"
          >
            Paste a reel
          </Link>
          {email ? (
            <div className="flex items-center gap-4 sm:gap-6">
              <Link
                href="/recipes"
                className="inline-flex min-h-12 items-center border border-cast-iron px-4 py-2 font-display text-lg font-semibold text-cast-iron sm:text-xl"
              >
                My recipes
              </Link>
              <p className="hidden max-w-[18ch] truncate font-display text-lg text-cast-iron sm:block sm:text-xl">
                {email}
              </p>
              <form action={signOut}>
                <button
                  type="submit"
                  className="font-display text-lg font-medium text-cast-iron underline-offset-4 hover:underline sm:text-xl"
                >
                  Sign out
                </button>
              </form>
            </div>
          ) : (
            <Link
              href="/login"
              className="font-display text-lg font-medium text-cast-iron underline-offset-4 hover:underline sm:text-xl"
            >
              Log in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}

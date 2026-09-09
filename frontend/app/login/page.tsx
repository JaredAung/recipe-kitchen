import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { LoginForm } from "@/components/login-form";
import { safeNextPath } from "@/lib/auth/paths";
import { createClient } from "@/lib/supabase/server";

export const metadata: Metadata = {
  title: "Log in · Recipe Kitchen",
};

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const params = await searchParams;
  const callbackError =
    typeof params.error === "string" ? params.error.replaceAll("+", " ") : undefined;
  const next = typeof params.next === "string" ? safeNextPath(params.next) : undefined;

  if (data?.claims) {
    redirect(next ?? "/");
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-5 py-16 sm:px-8">
      <h1 className="font-display text-4xl font-semibold tracking-tight">Log in</h1>
      <p className="mt-4 max-w-[40ch] text-lg leading-8">
        Keep the cards from your reels on this stove. Same email next time you cook.
      </p>
      <LoginForm callbackError={callbackError} next={next} />
    </main>
  );
}

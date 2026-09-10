export function getSupabasePublicEnv() {
  const url =
    process.env["NEXT_PUBLIC_SUPABASE_URL"] || process.env["SUPABASE_URL"];
  const publishableKey =
    process.env["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"] ||
    process.env["SUPABASE_PUBLISHABLE_KEY"];

  if (!url || !publishableKey) {
    throw new Error(
      "Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in the repo-root .env",
    );
  }

  return { url, publishableKey };
}

export function getSupabaseSecretKey() {
  const secret = process.env.SUPABASE_SECRET_KEY?.trim();
  if (!secret) {
    throw new Error("SUPABASE_SECRET_KEY is missing");
  }
  return secret;
}

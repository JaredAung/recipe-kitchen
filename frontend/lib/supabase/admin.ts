import "server-only";

import { createClient } from "@supabase/supabase-js";

import { loadRootEnv } from "@/lib/utils/load-root-env";
import { getSupabasePublicEnv, getSupabaseSecretKey } from "@/lib/supabase/env";

loadRootEnv();

export function getSupabaseAdmin() {
  const { url } = getSupabasePublicEnv();
  return createClient(url, getSupabaseSecretKey(), {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

import "server-only";

import { createClient as createSupabaseClient } from "@supabase/supabase-js";

import { createClient } from "@/lib/supabase/server";
import { getSupabasePublicEnv } from "@/lib/supabase/env";

const UNAUTHORIZED = "Invalid or expired access token";

export class AuthRequiredError extends Error {
  readonly status = 401;

  constructor(message = UNAUTHORIZED) {
    super(message);
    this.name = "AuthRequiredError";
  }
}

export async function requireUserId(request: Request): Promise<string> {
  const header = request.headers.get("authorization");
  if (header) {
    const token = bearerToken(header);
    if (!token) {
      throw new AuthRequiredError();
    }
    return userIdFromAccessToken(token);
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user?.id) {
    throw new AuthRequiredError();
  }
  return data.user.id;
}

function bearerToken(header: string): string | null {
  const match = /^Bearer\s+(\S+)/i.exec(header.trim());
  return match?.[1] ?? null;
}

async function userIdFromAccessToken(token: string): Promise<string> {
  const { url, publishableKey } = getSupabasePublicEnv();
  const supabase = createSupabaseClient(url, publishableKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await supabase.auth.getUser(token);
  if (error || !data.user?.id) {
    throw new AuthRequiredError();
  }
  return data.user.id;
}

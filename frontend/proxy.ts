import type { NextRequest } from "next/server";

import { loadRootEnv } from "@/lib/utils/load-root-env";
import { updateSession } from "@/lib/supabase/proxy";

loadRootEnv();

export async function proxy(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};

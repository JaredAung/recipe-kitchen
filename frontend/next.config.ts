import path from "node:path";

import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";

import { loadRootEnv } from "./lib/utils/load-root-env";

loadEnvConfig(path.resolve(process.cwd(), ".."), process.env.NODE_ENV !== "production");
loadRootEnv();

const supabaseUrl = process.env.SUPABASE_URL ?? "";
const supabasePublishableKey = process.env.SUPABASE_PUBLISHABLE_KEY ?? "";
const apiUrl = process.env.API_URL?.replace(/\/$/, "");

process.env.NEXT_PUBLIC_SUPABASE_URL = supabaseUrl;
process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = supabasePublishableKey;

const nextConfig: NextConfig = {
  reactCompiler: true,
  env: {
    NEXT_PUBLIC_SUPABASE_URL: supabaseUrl,
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: supabasePublishableKey,
  },
  async rewrites() {
    if (!apiUrl) {
      return [];
    }
    return [
      {
        source: "/backend/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;

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
    // Ingest, recipe, and job status are Next Route Handlers under app/backend.
    return [
      { source: "/backend/audio", destination: `${apiUrl}/audio` },
      { source: "/backend/audio/:path*", destination: `${apiUrl}/audio/:path*` },
      { source: "/backend/video", destination: `${apiUrl}/video` },
      { source: "/backend/video/:path*", destination: `${apiUrl}/video/:path*` },
      { source: "/backend/health", destination: `${apiUrl}/health` },
      { source: "/backend/me", destination: `${apiUrl}/me` },
    ];
  },
};

export default nextConfig;

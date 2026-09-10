import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

function repoRoot(start = process.cwd()) {
  let dir = start;
  while (true) {
    if (existsSync(path.join(dir, "pyproject.toml"))) {
      return dir;
    }
    const parent = path.dirname(dir);
    if (parent === dir) {
      return path.resolve(start, "..");
    }
    dir = parent;
  }
}

const CANONICAL_KEYS = [
  "API_URL",
  "AWS_ACCESS_KEY_ID",
  "AWS_REGION",
  "AWS_SECRET_ACCESS_KEY",
  "SQS_QUEUE_URL",
  "SUPABASE_PUBLISHABLE_KEY",
  "SUPABASE_SECRET_KEY",
  "SUPABASE_URL",
] as const;

function parseEnvFile(contents: string) {
  const parsed: Record<string, string> = {};
  for (const line of contents.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const eq = trimmed.indexOf("=");
    if (eq === -1) {
      continue;
    }
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    parsed[key] = value;
  }
  return parsed;
}

function applyCanonicalNames(parsed: Record<string, string>) {
  const byLower = new Map<string, string>();
  for (const [key, value] of Object.entries(parsed)) {
    byLower.set(key.toLowerCase(), value);
  }
  for (const [key, value] of Object.entries(process.env)) {
    if (value && !byLower.has(key.toLowerCase())) {
      byLower.set(key.toLowerCase(), value);
    }
  }
  const aliases: Record<string, string> = {
    access_key_id: "AWS_ACCESS_KEY_ID",
    secret_access_key: "AWS_SECRET_ACCESS_KEY",
  };
  for (const [from, to] of Object.entries(aliases)) {
    if (!process.env[to]) {
      const value = byLower.get(from);
      if (value) {
        process.env[to] = value;
      }
    }
  }

  for (const key of CANONICAL_KEYS) {
    if (!process.env[key]) {
      const value = byLower.get(key.toLowerCase());
      if (value) {
        process.env[key] = value;
      }
    }
  }
}

export function loadRootEnv() {
  const envPath = path.join(repoRoot(), ".env");
  if (!existsSync(envPath)) {
    return;
  }

  const parsed = parseEnvFile(readFileSync(envPath, "utf8"));
  for (const [key, value] of Object.entries(parsed)) {
    if (!process.env[key]) {
      process.env[key] = value;
    }
  }
  applyCanonicalNames(parsed);

  if (!process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.SUPABASE_URL) {
    process.env.NEXT_PUBLIC_SUPABASE_URL = process.env.SUPABASE_URL;
  }
  if (
    !process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY &&
    process.env.SUPABASE_PUBLISHABLE_KEY
  ) {
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY =
      process.env.SUPABASE_PUBLISHABLE_KEY;
  }
}

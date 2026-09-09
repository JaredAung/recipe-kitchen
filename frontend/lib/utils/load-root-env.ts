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

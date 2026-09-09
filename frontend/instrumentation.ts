export async function register() {
  if (process.env.NEXT_RUNTIME === "edge") {
    return;
  }
  const { loadRootEnv } = await import("./lib/env/load-root-env");
  loadRootEnv();
}

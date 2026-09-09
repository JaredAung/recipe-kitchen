export async function register() {
  if (process.env.NEXT_RUNTIME === "edge") {
    return;
  }
  const { loadRootEnv } = await import("./lib/utils/load-root-env");
  loadRootEnv();
}

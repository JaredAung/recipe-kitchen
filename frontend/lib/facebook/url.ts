const FACEBOOK_HOSTS = new Set([
  "facebook.com",
  "www.facebook.com",
  "m.facebook.com",
  "web.facebook.com",
  "mbasic.facebook.com",
  "fb.com",
  "www.fb.com",
  "m.fb.com",
  "fb.watch",
]);

const VIDEO_PATHS = [
  /^\/reel\/[^/]+/i,
  /^\/reels\/[^/]+/i,
  /^\/watch\/?/i,
  /^\/share\/r\/[^/]+/i,
  /^\/share\/v\/[^/]+/i,
  /^\/[^/]+\/videos\/\d+/i,
  /^\/[^/]+\/reel\/[^/]+/i,
];

export class FacebookUrlError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FacebookUrlError";
  }
}

export function parseFacebookVideoUrl(url: string): string {
  const trimmed = url.trim();
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    throw new FacebookUrlError("URL must be a facebook.com, fb.com, or fb.watch link");
  }

  if (parsed.protocol !== "https:") {
    throw new FacebookUrlError("Facebook URL must use https");
  }

  const host = parsed.hostname.toLowerCase();
  if (!FACEBOOK_HOSTS.has(host)) {
    throw new FacebookUrlError("URL must be a facebook.com, fb.com, or fb.watch link");
  }

  const path = parsed.pathname || "/";
  if (host === "fb.watch") {
    if (!path.replace(/^\/+|\/+$/g, "")) {
      throw new FacebookUrlError("fb.watch URL is missing the video id");
    }
    return trimmed;
  }

  if (!VIDEO_PATHS.some((pattern) => pattern.test(path))) {
    throw new FacebookUrlError("URL must be a Facebook reel, watch, share, or video link");
  }

  return trimmed;
}

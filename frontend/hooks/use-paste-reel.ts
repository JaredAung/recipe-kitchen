"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type SubmitEvent } from "react";

import { ApiError } from "@/lib/api/client";
import { ingestFacebook } from "@/lib/api/ingest";

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function messageForError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.detail;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Something went wrong. Try again.";
}

export function usePasteReel() {
  const router = useRouter();
  const abortRef = useRef<AbortController | null>(null);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  function onUrlChange(value: string) {
    setUrl(value);
    if (error) {
      setError(null);
    }
  }

  async function onSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Paste a Facebook reel URL to extract a recipe.");
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setError(null);
    setBusy(true);

    try {
      const accepted = await ingestFacebook(trimmed, { signal: controller.signal });
      router.push(`/recipe/${accepted.job_id}`);
    } catch (caught) {
      if (isAbortError(caught) || controller.signal.aborted) {
        return;
      }
      setError(messageForError(caught));
      setBusy(false);
    }
  }

  return {
    url,
    onUrlChange,
    onSubmit,
    error,
    busy,
  };
}

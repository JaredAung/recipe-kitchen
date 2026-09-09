"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getJob } from "@/lib/api/jobs";

export function useJobPoller(jobId: string) {
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const job = await getJob(jobId);
        if (cancelled) {
          return;
        }
        if (job.status === "succeeded" || job.status === "failed") {
          router.refresh();
          return;
        }
      } catch {
        if (cancelled) {
          return;
        }
      }
      timer = setTimeout(() => {
        void tick();
      }, 2000);
    };

    timer = setTimeout(() => {
      void tick();
    }, 2000);

    return () => {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [jobId, router]);
}

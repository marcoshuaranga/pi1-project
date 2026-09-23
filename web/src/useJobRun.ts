import { useCallback, useRef, useState } from "react";
import { JobEnqueue, JobStatus, pollJob } from "./api";

/**
 * Owns the enqueue -> poll -> abort ritual shared by every ARQ job button
 * (KEDB generation, evaluation recompute): reset the in-flight abort
 * controller, track busy/status, and swallow AbortError from a superseded
 * or unmounted run. Callers own their own error/success messaging — that
 * differs per page and isn't part of the ritual.
 */
export function useJobRun() {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(
    async (enqueue: () => Promise<JobEnqueue>, queuedLabel: string): Promise<JobStatus | null> => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setBusy(true);
      setStatus(queuedLabel);
      try {
        const enqueued = await enqueue();
        setStatus(`Job ${enqueued.job_id} en cola — consultando cada 5s…`);
        return await pollJob(enqueued.job_id, {
          signal: controller.signal,
          onStatus: (job) => setStatus(`Job ${job.job_id}: ${job.status}`),
        });
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return null;
        throw e;
      } finally {
        setStatus("");
        setBusy(false);
      }
    },
    []
  );

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  return { busy, status, run, cancel };
}

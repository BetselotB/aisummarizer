import { useEffect, useState } from "react";
import { api } from "../api";
import type { JobLog } from "../types";

export function useJobLogs(jobId: string, enabled: boolean) {
  const [logs, setLogs] = useState<JobLog[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    try {
      const { logs: data } = await api.jobs.logs(jobId);
      setLogs(data);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    if (!jobId) return;
    setLoading(true);
    fetchLogs().finally(() => setLoading(false));
  }, [jobId]);

  useEffect(() => {
    if (!enabled || !jobId) return;
    const id = setInterval(fetchLogs, 2000);
    return () => clearInterval(id);
  }, [jobId, enabled]);

  return { logs, loading };
}

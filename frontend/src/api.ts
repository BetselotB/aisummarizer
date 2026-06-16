import type { Activity, ApiKey, Health, Job, JobLog } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      (data as { detail?: string }).detail ||
        (data as { message?: string }).message ||
        res.statusText
    );
  }
  return data as T;
}

export const api = {
  health: () => request<Health>("/api/health"),

  config: {
    get: () =>
      request<{
        llm_provider: string;
        gemini_model: string;
        openrouter_model: string;
        grok_model: string;
        model: string;
      }>("/api/config"),
    set: (partial: Record<string, string>) =>
      request("/api/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(partial),
      }),
  },

  state: {
    get: () => request<{ state: Record<string, unknown> }>("/api/state"),
    put: (state: Record<string, unknown>) =>
      request("/api/state", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state }),
      }),
  },

  keys: {
    list: () => request<{ keys: ApiKey[] }>("/api/keys"),
    bulk: (keys_text: string, label_prefix: string) =>
      request<{ added: number; rejected: { reason: string }[] }>(
        "/api/keys/bulk",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ keys_text, label_prefix }),
        }
      ),
    toggle: (id: string, enabled: boolean) =>
      request(`/api/keys/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      }),
    remove: (id: string) => request(`/api/keys/${id}`, { method: "DELETE" }),
  },

  jobs: {
    list: () => request<{ jobs: Job[] }>("/api/jobs"),
    logs: (id: string) => request<{ logs: JobLog[] }>(`/api/jobs/${id}/logs`),
    create: (form: FormData) =>
      request<{ job: Job }>("/api/jobs", { method: "POST", body: form }),
    createText: (
      title: string,
      extra_context: string,
      llm_provider?: string,
      detail_tier?: string
    ) =>
      request<{ job: Job }>("/api/jobs/text-only", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, extra_context, llm_provider, detail_tier }),
      }),
    resume: (id: string) =>
      request<{ resume_from: string }>(`/api/jobs/${id}/resume`, {
        method: "POST",
      }),
  },

  activity: {
    list: () => request<{ activity: Activity[] }>("/api/activity"),
    track: (kind: string, message: string) =>
      request("/api/activity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, message }),
      }),
  },
};

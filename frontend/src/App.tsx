import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Activity, ApiKey, AppPage, Health, Job } from "./types";
import { JobForm } from "./components/JobForm";
import { KeysPanel } from "./components/KeysPanel";
import { TasksPage } from "./components/TasksPage";
import { ActivityPanel } from "./components/ActivityPanel";
import { usePolling } from "./hooks/usePolling";

const LS = "aisg_v2";

export default function App() {
  const [page, setPage] = useState<AppPage>(() => {
    return (localStorage.getItem(`${LS}_page`) as AppPage) || "create";
  });
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return (localStorage.getItem(`${LS}_theme`) as "dark" | "light") || "dark";
  });
  const [health, setHealth] = useState<Health | null>(null);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [draft, setDraft] = useState({ title: "", context: "" });
  const [savedFlash, setSavedFlash] = useState(false);

  const toast = useCallback((msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3500);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [h, k, j, a] = await Promise.all([
        api.health(),
        api.keys.list(),
        api.jobs.list(),
        api.activity.list(),
      ]);
      setHealth(h);
      setKeys(k.keys);
      setJobs(j.jobs);
      setActivity(a.activity);
    } catch {
      /* offline */
    }
  }, []);

  const hasActive = jobs.some(
    (j) => j.status === "running" || j.status === "pending"
  );

  usePolling(refresh, hasActive ? 2000 : 8000, true);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(`${LS}_theme`, theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(`${LS}_page`, page);
  }, [page]);

  useEffect(() => {
    refresh();
    api.state.get().then(({ state }) => {
      if (state.jobTitle) setDraft((d) => ({ ...d, title: String(state.jobTitle) }));
      if (state.jobContext) setDraft((d) => ({ ...d, context: String(state.jobContext) }));
    });
  }, [refresh]);

  useEffect(() => {
    const t = setTimeout(() => {
      api.state.put({ jobTitle: draft.title, jobContext: draft.context }).catch(() => {});
      setSavedFlash(true);
      setTimeout(() => setSavedFlash(false), 1500);
    }, 600);
    return () => clearTimeout(t);
  }, [draft]);

  const onJobCreated = (job: Job) => {
    refresh();
    setPage("tasks");
    localStorage.setItem(
      "openJobTabs",
      JSON.stringify([
        ...new Set([
          ...JSON.parse(localStorage.getItem("openJobTabs") || "[]"),
          job.id,
        ]),
      ])
    );
  };

  const activeCount = jobs.filter(
    (j) => j.status === "running" || j.status === "pending"
  ).length;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="logo">SG</span>
          <div>
            <h1>Study Guide</h1>
            <p>PDF → exam-ready notes</p>
          </div>
        </div>
        <nav className="main-nav">
          {(
            [
              ["create", "Create"],
              ["tasks", `Tasks${activeCount ? ` (${activeCount})` : ""}`],
              ["settings", "Keys"],
              ["activity", "Activity"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`nav-btn ${page === id ? "active" : ""}`}
              onClick={() => setPage(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="header-actions">
          {savedFlash && <span className="saved-indicator">saved</span>}
          <button
            type="button"
            className="btn ghost icon"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          >
            {theme === "dark" ? "◐" : "●"}
          </button>
          <div className={`status-pill ${health && (health.api_keys ?? health.gemini_keys) > 0 ? "ok" : "bad"}`}>
            {health
              ? `${health.llm_provider || "gemini"} · ${health.api_keys ?? health.gemini_keys} keys · ${health.model || health.gemini_model || "?"}`
              : "…"}
          </div>
        </div>
      </header>

      <main className={`main-page page-${page}`}>
        {page === "create" && (
          <div className="grid">
            <JobForm
              onCreated={onJobCreated}
              toast={toast}
              draft={draft}
              onDraftChange={setDraft}
              defaultProvider={(health?.llm_provider as "gemini" | "openrouter" | "grok") || "gemini"}
            />
            <KeysPanel
              keys={keys}
              provider={health?.llm_provider || "gemini"}
              geminiModel={health?.gemini_model || "gemini-2.5-flash"}
              openrouterModel={health?.openrouter_model || "google/gemini-2.0-flash-exp:free"}
              grokModel={health?.grok_model || "grok-4.3"}
              onRefresh={refresh}
              toast={toast}
            />
          </div>
        )}

        {page === "tasks" && (
          <TasksPage jobs={jobs} onJobsChange={refresh} toast={toast} />
        )}

        {page === "settings" && (
          <div className="grid single">
            <KeysPanel
              keys={keys}
              provider={health?.llm_provider || "gemini"}
              geminiModel={health?.gemini_model || "gemini-2.5-flash"}
              openrouterModel={health?.openrouter_model || "google/gemini-2.0-flash-exp:free"}
              grokModel={health?.grok_model || "grok-4.3"}
              onRefresh={refresh}
              toast={toast}
            />
          </div>
        )}

        {page === "activity" && (
          <div className="grid">
            <ActivityPanel items={activity} />
          </div>
        )}
      </main>

      {toastMsg && <div className="toast">{toastMsg}</div>}
    </div>
  );
}

import { useEffect, useState } from "react";
import { api } from "../api";
import type { Job } from "../types";
import { JobDetail } from "./JobDetail";

interface Props {
  jobs: Job[];
  onJobsChange: () => void;
  toast: (msg: string) => void;
}

export function TasksPage({ jobs, onJobsChange, toast }: Props) {
  const [openTabs, setOpenTabs] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("openJobTabs") || "[]");
    } catch {
      return [];
    }
  });
  const [activeId, setActiveId] = useState<string | null>(null);
  const [resuming, setResuming] = useState<string | null>(null);

  // Auto-open running/pending jobs
  useEffect(() => {
    const active = jobs.filter((j) => j.status === "running" || j.status === "pending");
    if (active.length === 0) return;
    setOpenTabs((prev) => {
      const next = new Set([...prev, ...active.map((j) => j.id)]);
      const arr = [...next];
      localStorage.setItem("openJobTabs", JSON.stringify(arr));
      return arr;
    });
    setActiveId((cur) => cur ?? active[0]?.id ?? null);
  }, [jobs]);

  const openJob = (id: string) => {
    setOpenTabs((prev) => {
      if (prev.includes(id)) return prev;
      const next = [...prev, id];
      localStorage.setItem("openJobTabs", JSON.stringify(next));
      return next;
    });
    setActiveId(id);
  };

  const closeTab = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenTabs((prev) => {
      const next = prev.filter((t) => t !== id);
      localStorage.setItem("openJobTabs", JSON.stringify(next));
      if (activeId === id) {
        setActiveId(next[next.length - 1] ?? null);
      }
      return next;
    });
  };

  const handleResume = async (id: string) => {
    setResuming(id);
    try {
      const res = await api.jobs.resume(id);
      toast(`Resuming from ${res.resume_from}`);
      onJobsChange();
      openJob(id);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Resume failed");
    } finally {
      setResuming(null);
    }
  };

  const tabJobs = openTabs
    .map((id) => jobs.find((j) => j.id === id))
    .filter((j): j is Job => !!j);

  const activeJob = activeId ? jobs.find((j) => j.id === activeId) : null;

  const recentNotOpen = jobs.filter((j) => !openTabs.includes(j.id)).slice(0, 12);

  return (
    <div className="tasks-page">
      <div className="task-tabs-bar">
        {tabJobs.map((job) => (
          <button
            key={job.id}
            type="button"
            className={`task-tab ${activeId === job.id ? "active" : ""} ${job.status}`}
            onClick={() => setActiveId(job.id)}
          >
            <span className={`tab-dot ${job.status}`} />
            <span className="tab-title">{job.title}</span>
            <span className="tab-pct">{Math.round(job.progress)}%</span>
            <span
              className="tab-close"
              onClick={(e) => closeTab(job.id, e)}
              role="button"
              tabIndex={0}
            >
              ×
            </span>
          </button>
        ))}
        {tabJobs.length === 0 && (
          <span className="muted pad">No open tasks — start a job or pick one below</span>
        )}
      </div>

      <div className="tasks-body">
        {activeJob ? (
          <JobDetail
            job={activeJob}
            onResume={handleResume}
            resuming={resuming === activeJob.id}
          />
        ) : (
          <div className="empty-state">
            <p>Select a task tab or open a job from history</p>
          </div>
        )}
      </div>

      {recentNotOpen.length > 0 && (
        <div className="history-strip">
          <span className="history-label">Open in tab:</span>
          {recentNotOpen.map((job) => (
            <button
              key={job.id}
              type="button"
              className={`history-chip ${job.status}`}
              onClick={() => openJob(job.id)}
            >
              {job.title}
              <span className={`chip-status ${job.status}`}>{job.status}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

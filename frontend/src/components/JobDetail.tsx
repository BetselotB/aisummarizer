import { useState } from "react";
import type { Job } from "../types";
import { LogPanel } from "./LogPanel";
import { useJobLogs } from "../hooks/useJobLogs";

function formatDuration(sec?: number | null) {
  if (sec == null) return "—";
  if (sec < 60) return `${sec}s`;
  return `${Math.floor(sec / 60)}m ${sec % 60}s`;
}

function stepIcon(status: string) {
  if (status === "done") return "✓";
  if (status === "running") return "→";
  if (status === "failed") return "✗";
  return "·";
}

interface Props {
  job: Job;
  onResume: (id: string) => Promise<void>;
  resuming?: boolean;
}

export function JobDetail({ job, onResume, resuming }: Props) {
  const [stepsOpen, setStepsOpen] = useState(
    job.status === "running" || job.status === "failed"
  );
  const isLive = job.status === "running" || job.status === "pending";
  const { logs, loading } = useJobLogs(job.id, isLive);

  const pct =
    job.status === "completed" ? 100 : Math.min(99, Math.round(job.progress || 0));
  const stats = job.stats;
  const elapsed =
    stats?.elapsed_seconds ??
    (job.started_at && isLive
      ? Math.floor((Date.now() - new Date(job.started_at).getTime()) / 1000)
      : null);

  return (
    <div className={`job-detail ${job.status}`}>
      <div className="job-detail-head">
        <div>
          <h3>{job.title}</h3>
          <p className="meta">
            {new Date(job.created_at).toLocaleString()} · {job.id.slice(0, 8)}
            {job.llm_provider && (
              <> · <span className="badge">{job.llm_provider}</span></>
            )}
            {job.detail_tier && (
              <> · <span className="badge">{job.detail_tier}</span></>
            )}
          </p>
        </div>
        <span className={`status ${job.status}`}>{job.status}</span>
      </div>

      <div className="stats-grid">
        <div className="stat-box">
          <div className="stat-label">Progress</div>
          <div className="stat-value">{pct}%</div>
        </div>
        <div className="stat-box">
          <div className="stat-label">Elapsed</div>
          <div className="stat-value">{formatDuration(elapsed)}</div>
        </div>
        <div className="stat-box">
          <div className="stat-label">API calls</div>
          <div className="stat-value">{stats?.api_calls ?? 0}</div>
        </div>
        <div className="stat-box">
          <div className="stat-label">Chapters</div>
          <div className="stat-value">
            {stats?.chapters_done ?? job.chapters_saved ?? 0}/
            {stats?.chapters_total ?? job.chapters_total ?? "—"}
          </div>
        </div>
      </div>

      <div className="progress-wrap">
        <div className="progress-header">
          <span>{job.message || "Working…"}</span>
          <span>{pct}%</span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${pct}%`, transition: "width 0.5s ease" }}
          />
        </div>
      </div>

      {stats?.steps && stats.steps.length > 0 && (
        <>
          <button
            type="button"
            className="btn ghost sm"
            onClick={() => setStepsOpen((o) => !o)}
          >
            {stepsOpen ? "Hide" : "Show"} steps ({stats.steps.length})
          </button>
          {stepsOpen && (
            <ul className="step-list">
              {stats.steps.map((s) => (
                <li key={s.id} className={s.status}>
                  <span className={`step-icon ${s.status}`}>{stepIcon(s.status)}</span>
                  <div>
                    {s.label}
                    {s.error && <div className="step-error">{s.error}</div>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {job.status === "failed" && job.error && (
        <div className="error-banner">{job.error.split("\n")[0]}</div>
      )}

      {job.can_resume && (
        <div className="job-actions">
          <button
            type="button"
            className="btn primary sm"
            disabled={resuming}
            onClick={() => onResume(job.id)}
          >
            {resuming ? "Resuming…" : "Resume job"}
          </button>
        </div>
      )}

      {job.status === "completed" && (
        <div className="job-actions">
          <a className="btn ghost sm" href={`/api/jobs/${job.id}/download`}>
            Download PDF
          </a>
          <a className="btn ghost sm" href={`/api/jobs/${job.id}/document.json`}>
            Download JSON
          </a>
        </div>
      )}

      <LogPanel logs={logs} loading={loading && isLive} />
    </div>
  );
}

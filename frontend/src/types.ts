export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface JobStep {
  id: string;
  label: string;
  status: string;
  error?: string;
}

export interface JobStats {
  current_step?: string;
  api_calls?: number;
  source_chars?: number;
  chapters_total?: number;
  chapters_done?: number;
  source_file_names?: string[];
  steps?: JobStep[];
  error_step?: string;
  elapsed_seconds?: number;
}

export interface Job {
  id: string;
  title: string;
  status: JobStatus;
  progress: number;
  message: string;
  error?: string | null;
  pdf_path?: string | null;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  stats?: JobStats | null;
  can_resume?: boolean;
  resume_from?: string;
  chapters_saved?: number;
  chapters_total?: number;
}

export interface JobLog {
  level: string;
  message: string;
  created_at: string;
}

export interface ApiKey {
  id: string;
  label: string;
  masked_key: string;
  enabled: number;
  requests_count: number;
  last_error?: string | null;
}

export interface Activity {
  id: number;
  kind: string;
  message: string;
  created_at: string;
}

export interface Health {
  status: string;
  gemini_keys: number;
  gemini_model: string;
  active_jobs: string[];
}

export type AppPage = "create" | "tasks" | "settings" | "activity";

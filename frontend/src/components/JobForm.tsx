import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { DetailTier, Job } from "../types";

type Provider = "gemini" | "openrouter" | "grok";

const TIER_OPTIONS: { value: DetailTier; label: string; hint: string }[] = [
  { value: "concise", label: "Concise", hint: "Quick review — essentials only" },
  { value: "standard", label: "Standard", hint: "Balanced exam notes" },
  { value: "detailed", label: "Detailed", hint: "AI master plan + in-depth chapters" },
  { value: "comprehensive", label: "Comprehensive", hint: "Full section-by-section breakdown" },
];

interface Props {
  onCreated: (job: Job) => void;
  toast: (msg: string) => void;
  draft: { title: string; context: string };
  onDraftChange: (d: { title: string; context: string }) => void;
  defaultProvider?: Provider;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function JobForm({ onCreated, toast, draft, onDraftChange, defaultProvider = "gemini" }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [provider, setProvider] = useState<Provider>(defaultProvider);
  const inputRef = useRef<HTMLInputElement>(null);
  const [textMode, setTextMode] = useState(false);
  const [textTitle, setTextTitle] = useState("");
  const [textBody, setTextBody] = useState("");
  const [detailTier, setDetailTier] = useState<DetailTier>("standard");

  useEffect(() => {
    setProvider(defaultProvider);
  }, [defaultProvider]);

  const fileKey = (f: File) => `${f.name}::${f.size}::${f.lastModified}`;

  const addFiles = useCallback((incoming: FileList | File[]) => {
    setFiles((prev) => {
      const existing = new Set(prev.map(fileKey));
      const next = [...prev];
      for (const f of Array.from(incoming)) {
        if (!f.name.toLowerCase().endsWith(".pdf")) {
          toast(`Skipped non-PDF: ${f.name}`);
          continue;
        }
        const k = fileKey(f);
        if (!existing.has(k)) {
          existing.add(k);
          next.push(f);
        }
      }
      return next;
    });
  }, [toast]);

  const submitPdf = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!files.length) {
      toast("Add at least one PDF");
      return;
    }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("title", draft.title.trim());
      fd.append("extra_context", draft.context.trim());
      fd.append("llm_provider", provider);
      fd.append("detail_tier", detailTier);
      files.forEach((f) => fd.append("files", f, f.name));
      const { job } = await api.jobs.create(fd);
      toast("Job started");
      setFiles([]);
      onCreated(job);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed");
    } finally {
      setSubmitting(false);
    }
  };

  const submitText = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const { job } = await api.jobs.createText(textTitle.trim(), textBody.trim(), provider, detailTier);
      toast("Text job started");
      onCreated(job);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card animate-in">
      <h2>New study guide</h2>
      {!textMode ? (
        <form onSubmit={submitPdf}>
          <label>
            AI provider
            <select value={provider} onChange={(e) => setProvider(e.target.value as Provider)}>
              <option value="gemini">Gemini</option>
              <option value="openrouter">OpenRouter</option>
              <option value="grok">Grok (x.ai)</option>
            </select>
          </label>

          <label>
            Detail level
            <select value={detailTier} onChange={(e) => setDetailTier(e.target.value as DetailTier)}>
              {TIER_OPTIONS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label} — {t.hint}
                </option>
              ))}
            </select>
          </label>

          <label>
            Title
            <input
              value={draft.title}
              onChange={(e) => onDraftChange({ ...draft, title: e.target.value })}
              placeholder="Web Programming Final Exam"
              required
            />
          </label>

          <label>
            PDF files
            <div
              className={`drop-zone ${dragOver ? "drag-over" : ""}`}
              onClick={() => inputRef.current?.click()}
              onDragEnter={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
              }}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,application/pdf"
                multiple
                hidden
                onChange={(e) => {
                  if (e.target.files?.length) addFiles(e.target.files);
                  e.target.value = "";
                }}
              />
              <span className="drop-icon">+</span>
              <p className="drop-title">
                {files.length
                  ? `${files.length} file(s) selected`
                  : "Drag & drop PDFs here"}
              </p>
              <p className="drop-sub">or click to browse — adds to list</p>
            </div>
            {files.length > 0 && (
              <ul className="file-list">
                {files.map((f, i) => (
                  <li key={fileKey(f)}>
                    <span className="file-name">{f.name}</span>
                    <span className="file-meta">{formatSize(f.size)}</span>
                    <button
                      type="button"
                      className="remove-file"
                      onClick={(e) => {
                        e.stopPropagation();
                        setFiles((p) => p.filter((_, j) => j !== i));
                      }}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </label>

          <label>
            Extra context <span className="optional">optional</span>
            <textarea
              rows={4}
              value={draft.context}
              onChange={(e) => onDraftChange({ ...draft, context: e.target.value })}
              placeholder="Exam focus, topics to emphasize…"
            />
          </label>

          <button type="submit" className="btn primary" disabled={submitting}>
            {submitting ? "Starting…" : "Generate study guide"}
          </button>
        </form>
      ) : (
        <form onSubmit={submitText}>
          <label>
            AI provider
            <select value={provider} onChange={(e) => setProvider(e.target.value as Provider)}>
              <option value="gemini">Gemini</option>
              <option value="openrouter">OpenRouter</option>
              <option value="grok">Grok (x.ai)</option>
            </select>
          </label>
          <label>
            Detail level
            <select value={detailTier} onChange={(e) => setDetailTier(e.target.value as DetailTier)}>
              {TIER_OPTIONS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label} — {t.hint}
                </option>
              ))}
            </select>
          </label>

          <label>
            Title
            <input
              value={textTitle}
              onChange={(e) => setTextTitle(e.target.value)}
              required
            />
          </label>
          <label>
            Source text
            <textarea
              rows={8}
              value={textBody}
              onChange={(e) => setTextBody(e.target.value)}
              required
            />
          </label>
          <button type="submit" className="btn secondary" disabled={submitting}>
            Generate from text
          </button>
        </form>
      )}

      <button
        type="button"
        className="link-btn block"
        onClick={() => setTextMode((m) => !m)}
      >
        {textMode ? "← Back to PDF upload" : "Or paste text instead of PDF →"}
      </button>
    </div>
  );
}

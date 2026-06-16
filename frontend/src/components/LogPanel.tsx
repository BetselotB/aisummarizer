import { useEffect, useRef } from "react";
import type { JobLog } from "../types";

interface Props {
  logs: JobLog[];
  loading?: boolean;
}

export function LogPanel({ logs, loading }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  const handleScroll = () => {
    const el = ref.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottom.current = dist < 48;
  };

  useEffect(() => {
    const el = ref.current;
    if (!el || !stickToBottom.current) return;
    el.scrollTop = el.scrollHeight;
  }, [logs]);

  return (
    <div className="log-panel">
      <div className="log-panel-head">
        <span>Live logs</span>
        {loading && <span className="pulse-dot" />}
      </div>
      <div
        ref={ref}
        className="log-panel-body"
        onScroll={handleScroll}
      >
        {logs.length === 0 ? (
          <div className="muted">No logs yet</div>
        ) : (
          logs.map((l, i) => (
            <div
              key={`${l.created_at}-${i}`}
              className={l.level === "error" ? "log-line error" : "log-line"}
            >
              <span className="log-time">{l.created_at.slice(11, 19)}</span>
              {l.message}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

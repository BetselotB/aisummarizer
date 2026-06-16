import type { Activity } from "../types";

export function ActivityPanel({ items }: { items: Activity[] }) {
  const list = [...items].reverse().slice(0, 60);
  return (
    <div className="card animate-in span-2">
      <div className="card-head">
        <h2>Activity log</h2>
        <span className="badge">{items.length} events</span>
      </div>
      <ul className="activity-list">
        {list.length === 0 ? (
          <li className="empty">No activity yet</li>
        ) : (
          list.map((a) => (
            <li key={a.id}>
              <div className="act-time">
                {new Date(a.created_at).toLocaleString()} · {a.kind}
              </div>
              <div className="act-msg">{a.message}</div>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

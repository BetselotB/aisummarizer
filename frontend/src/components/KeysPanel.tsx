import { useState } from "react";
import { api } from "../api";
import type { ApiKey } from "../types";

interface Props {
  keys: ApiKey[];
  model: string;
  onRefresh: () => void;
  toast: (msg: string) => void;
}

const MODELS = [
  "gemini-2.5-flash",
  "gemini-2.5-flash-lite",
  "gemini-2.0-flash",
  "gemini-1.5-flash",
];

export function KeysPanel({ keys, model, onRefresh, toast }: Props) {
  const [bulk, setBulk] = useState("");
  const [prefix, setPrefix] = useState("Gemini");

  const addBulk = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.keys.bulk(bulk, prefix);
      toast(`Added ${res.added} key(s)`);
      if (res.rejected?.length) {
        toast(`${res.rejected.length} rejected — use AIza keys only`);
      }
      setBulk("");
      onRefresh();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed");
    }
  };

  const setModel = async (m: string) => {
    try {
      await api.config.set(m);
      onRefresh();
      toast(`Model: ${m}`);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed");
    }
  };

  return (
    <div className="card animate-in">
      <div className="card-head">
        <h2>Gemini API keys</h2>
        <span className="badge">{keys.length} keys</span>
      </div>
      <p className="desc">
        Use <strong>AIza…</strong> keys from different Google accounts — same project shares quota.
      </p>

      <label>
        Model
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          {MODELS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>

      <form onSubmit={addBulk}>
        <label>
          Paste keys (one per line)
          <textarea
            rows={4}
            value={bulk}
            onChange={(e) => setBulk(e.target.value)}
            placeholder="AIza…"
          />
        </label>
        <div className="row">
          <input value={prefix} onChange={(e) => setPrefix(e.target.value)} />
          <button type="submit" className="btn secondary">
            Add keys
          </button>
        </div>
      </form>

      <ul className="key-list">
        {keys.length === 0 ? (
          <li className="empty">No keys yet</li>
        ) : (
          keys.map((k) => (
            <li key={k.id}>
              <div>
                <div>
                  {k.label} {!k.enabled && "(off)"}
                </div>
                <div className="meta">
                  {k.masked_key} · {k.requests_count} calls
                </div>
                {!k.masked_key.startsWith("AIza") && (
                  <div className="meta warn">Invalid format — remove</div>
                )}
              </div>
              <div className="actions">
                <button
                  type="button"
                  className="btn ghost sm"
                  onClick={async () => {
                    await api.keys.toggle(k.id, !k.enabled);
                    onRefresh();
                  }}
                >
                  {k.enabled ? "Disable" : "Enable"}
                </button>
                <button
                  type="button"
                  className="btn danger sm"
                  onClick={async () => {
                    await api.keys.remove(k.id);
                    onRefresh();
                  }}
                >
                  Remove
                </button>
              </div>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

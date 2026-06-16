import { useState } from "react";
import { api } from "../api";
import type { ApiKey } from "../types";

interface Props {
  keys: ApiKey[];
  provider: string;
  geminiModel: string;
  openrouterModel: string;
  grokModel: string;
  onRefresh: () => void;
  toast: (msg: string) => void;
}

const GEMINI_MODELS = [
  "gemini-2.5-flash",
  "gemini-2.5-flash-lite",
  "gemini-2.0-flash",
  "gemini-1.5-flash",
];

const OPENROUTER_MODELS = [
  "google/gemini-2.0-flash-exp:free",
  "google/gemini-2.5-flash-preview:free",
  "meta-llama/llama-3.3-70b-instruct:free",
  "openai/gpt-4o-mini",
  "openai/gpt-4o",
];

const GROK_MODELS = ["grok-4.3", "grok-4", "grok-3-mini"];

export function KeysPanel({
  keys,
  provider,
  geminiModel,
  openrouterModel,
  grokModel,
  onRefresh,
  toast,
}: Props) {
  const [bulk, setBulk] = useState("");
  const [prefix, setPrefix] = useState("API");

  const addBulk = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.keys.bulk(bulk, prefix);
      toast(`Added ${res.added} key(s)`);
      if (res.rejected?.length) {
        toast(`${res.rejected.length} rejected — use AIza…, sk-or-v1-…, or xai-… keys`);
      }
      setBulk("");
      onRefresh();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed");
    }
  };

  const saveConfig = async (partial: Record<string, string>) => {
    try {
      await api.config.set(partial);
      onRefresh();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed");
    }
  };

  return (
    <div className="card animate-in">
      <div className="card-head">
        <h2>API keys</h2>
        <span className="badge">{keys.length} keys</span>
      </div>
      <p className="desc">
        Add <strong>AIza…</strong> (Gemini), <strong>sk-or-v1-…</strong> (OpenRouter), or{" "}
        <strong>xai-…</strong> (Grok) keys.
      </p>

      <label>
        Provider
        <select
          value={provider}
          onChange={(e) => saveConfig({ llm_provider: e.target.value })}
        >
          <option value="gemini">Gemini</option>
          <option value="openrouter">OpenRouter</option>
          <option value="grok">Grok</option>
        </select>
      </label>

      {provider === "gemini" && (
        <label>
          Gemini model
          <select
            value={geminiModel}
            onChange={(e) => saveConfig({ gemini_model: e.target.value })}
          >
            {GEMINI_MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      )}

      {provider === "openrouter" && (
        <label>
          OpenRouter model
          <select
            value={openrouterModel}
            onChange={(e) => saveConfig({ openrouter_model: e.target.value })}
          >
            {OPENROUTER_MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      )}

      {provider === "grok" && (
        <label>
          Grok model
          <select
            value={grokModel}
            onChange={(e) => saveConfig({ grok_model: e.target.value })}
          >
            {GROK_MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      )}

      <form onSubmit={addBulk}>
        <label>
          Paste keys (one per line)
          <textarea
            rows={4}
            value={bulk}
            onChange={(e) => setBulk(e.target.value)}
            placeholder="AIza…, sk-or-v1-…, or xai-…"
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
                  {k.label} <span className="badge">{k.provider}</span>{" "}
                  {!k.enabled && "(off)"}
                </div>
                <div className="meta">
                  {k.masked_key} · {k.requests_count} calls
                </div>
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

import { useEffect, useRef } from "react";

export function usePolling(callback: () => void, intervalMs: number, enabled: boolean) {
  const cb = useRef(callback);
  cb.current = callback;

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => cb.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}

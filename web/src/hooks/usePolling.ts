import { useEffect, useRef } from 'react';

export function usePolling(callback: () => Promise<void> | void, intervalMs: number, enabled: boolean) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return undefined;
    const timer = window.setInterval(() => {
      void savedCallback.current();
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [enabled, intervalMs]);
}

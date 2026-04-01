"use client";

import { useCallback, useEffect, useState } from "react";

const TOAST_EVENT = "meetnote:toast";
const DEFAULT_DURATION_MS = 3200;

const toast = (message, options = {}) => {
  if (typeof window === "undefined") return;
  const text = typeof message === "string" ? message.trim() : "";
  if (!text) return;
  const durationMs =
    Number.isFinite(options.durationMs) && options.durationMs > 0
      ? options.durationMs
      : DEFAULT_DURATION_MS;
  window.dispatchEvent(
    new CustomEvent(TOAST_EVENT, {
      detail: { message: text, durationMs },
    }),
  );
};

const useToastHost = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    const handler = (evt) => {
      const message = evt?.detail?.message;
      const durationMs = evt?.detail?.durationMs;
      if (typeof message !== "string" || !message.trim()) return;
      const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const ttl = Number.isFinite(durationMs) ? durationMs : DEFAULT_DURATION_MS;

      setItems((prev) => [...prev, { id, message }]);
      window.setTimeout(() => {
        setItems((prev) => prev.filter((t) => t.id !== id));
      }, ttl);
    };

    window.addEventListener(TOAST_EVENT, handler);
    return () => window.removeEventListener(TOAST_EVENT, handler);
  }, []);

  const dismiss = useCallback((id) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { items, dismiss };
};

export { toast, useToastHost };


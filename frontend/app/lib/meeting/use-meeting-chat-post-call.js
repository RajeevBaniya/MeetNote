"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const buildClientId = () =>
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

const useMeetingChatPostCall = (meetingId, jwt, isAvailable) => {
  const [messages, setMessages] = useState([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [sendError, setSendError] = useState(null);
  const [isSending, setIsSending] = useState(false);
  const [latestResponseMode, setLatestResponseMode] = useState(null);

  const abortControllerRef = useRef(null);
  const retryingIdsRef = useRef(new Set());

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;

  // Load persisted history once when the chat becomes available
  useEffect(() => {
    if (!meetingId || !jwt || !isAvailable) return;
    if (!apiUrl) return;

    let cancelled = false;
    setHistoryLoaded(false);
    setHistoryError(null);

    fetch(`${apiUrl}/meetings/${meetingId}/chat/history`, {
      headers: { Authorization: `Bearer ${jwt}` },
    })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("Failed to load history"))))
      .then((data) => {
        if (cancelled) return;
        const loaded = Array.isArray(data.history) ? data.history : [];
        setMessages(
          loaded.map((m) => ({
            clientId: buildClientId(),
            role: m.role,
            content: m.content,
            failed: false,
            retrying: false,
          }))
        );
        setHistoryLoaded(true);
      })
      .catch((err) => {
        if (!cancelled) {
          setHistoryError(err.message || "Could not load conversation history.");
          setHistoryLoaded(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [meetingId, jwt, isAvailable, apiUrl]);

  // Cancel any in-flight request on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      const trimmed = typeof text === "string" ? text.trim() : "";
      if (!trimmed || isSending || !apiUrl) return;

      const clientId = buildClientId();
      const userEntry = { clientId, role: "user", content: trimmed, failed: false, retrying: false };
      const pendingEntry = {
        clientId: buildClientId(),
        role: "assistant",
        content: "",
        failed: false,
        retrying: false,
        pending: true,
      };

      setMessages((prev) => [...prev, userEntry, pendingEntry]);
      setIsSending(true);
      setSendError(null);

      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const res = await fetch(`${apiUrl}/meetings/${meetingId}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${jwt}`,
          },
          body: JSON.stringify({ message: trimmed }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || body.detail || "The assistant could not respond.");
        }

        const data = await res.json();
        const assistantContent = data.response || "";
        const responseMode = data.response_mode || null;

        if (responseMode) {
          setLatestResponseMode(responseMode);
        }

        setMessages((prev) =>
          prev
            .filter((m) => !(m.pending && m.role === "assistant"))
            .concat({
              clientId: buildClientId(),
              role: "assistant",
              content: assistantContent,
              failed: false,
              retrying: false,
            })
        );
      } catch (err) {
        if (err.name === "AbortError") {
          setMessages((prev) => prev.filter((m) => !m.pending));
          return;
        }
        const errorMessage = err.message || "Something went wrong. Please try again.";
        setSendError(errorMessage);
        setMessages((prev) =>
          prev
            .filter((m) => !m.pending)
            .map((m) => (m.clientId === clientId ? { ...m, failed: true } : m))
        );
      } finally {
        setIsSending(false);
      }
    },
    [meetingId, jwt, isSending, apiUrl]
  );

  const retryMessage = useCallback(
    async (clientId, text) => {
      if (retryingIdsRef.current.has(clientId)) return;
      if (isSending) return;

      retryingIdsRef.current.add(clientId);
      setMessages((prev) =>
        prev.map((m) => (m.clientId === clientId ? { ...m, retrying: true, failed: false } : m))
      );

      try {
        await sendMessage(text);
        setMessages((prev) => prev.filter((m) => m.clientId !== clientId));
      } catch {
        setMessages((prev) =>
          prev.map((m) => (m.clientId === clientId ? { ...m, retrying: false, failed: true } : m))
        );
      } finally {
        retryingIdsRef.current.delete(clientId);
      }
    },
    [isSending, sendMessage]
  );

  return {
    messages,
    historyLoaded,
    historyError,
    sendError,
    isSending,
    latestResponseMode,
    sendMessage,
    retryMessage,
  };
};

export default useMeetingChatPostCall;

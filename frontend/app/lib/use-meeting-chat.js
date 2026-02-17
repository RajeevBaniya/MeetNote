"use client";

import { useCallback, useEffect, useRef, useState } from "react";

function buildChatWsUrl(apiUrl, meetingId, jwt) {
  const base = (apiUrl || "").replace(/\/$/, "");
  const wsBase = base.replace(/^http:\/\//i, "ws://").replace(/^https:\/\//i, "wss://");
  const token = encodeURIComponent(jwt || "");
  return `${wsBase}/ws/meetings/${meetingId}/chat?token=${token}`;
}

function closeReasonToMessage(code, reason) {
  const r = (reason || "").toLowerCase();
  if (code === 4401 || r.includes("token") || r.includes("unauthorized")) {
    return "Connection failed. Sign in again.";
  }
  if (code === 4403 || r.includes("removed")) {
    return "You were removed from this meeting. Chat is unavailable.";
  }
  if (code === 4403 || r.includes("not approved")) {
    return "You are not approved to join this meeting. Chat is unavailable.";
  }
  if (code === 4400 || r.includes("meeting ended")) {
    return "Meeting has ended. Chat is unavailable.";
  }
  if (r) return r;
  return "Connection closed.";
}

const ASSISTANT_USER_ID = "system:assistant";
const ASSISTANT_DISPLAY_NAME = "Assistant";

function isAssistantMessage(message) {
  if (!message) return false;
  const id = typeof message.user_id === "string" ? message.user_id : "";
  const name = typeof message.display_name === "string" ? message.display_name : "";
  return id === ASSISTANT_USER_ID || name === ASSISTANT_DISPLAY_NAME;
}

export function useMeetingChat(meetingId, jwt, isChatTabVisible = false) {
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const wsRef = useRef(null);
  const mountedRef = useRef(true);
  const isChatVisibleRef = useRef(isChatTabVisible);
  isChatVisibleRef.current = isChatTabVisible;

  const markChatRead = useCallback(() => {
    setUnreadCount(0);
  }, []);

  const sendMessage = useCallback(
    (text) => {
      const t = typeof text === "string" ? text.trim() : "";
      if (!t || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      try {
        wsRef.current.send(JSON.stringify({ type: "message", text: t }));
      } catch {
        // ignore
      }
    },
    []
  );

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!meetingId || !jwt) {
      setConnected(false);
      setConnectionError(null);
      setMessages([]);
      return;
    }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      setConnectionError("API URL not configured");
      return;
    }
    setConnectionError(null);
    setMessages([]);
    const url = buildChatWsUrl(apiUrl, meetingId, jwt);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnected(true);
      setConnectionError(null);
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        if (data.type === "history" && Array.isArray(data.messages)) {
          setMessages(data.messages.filter((message) => !isAssistantMessage(message)));
          return;
        }
        if (data.type === "chat_message") {
          if (isAssistantMessage(data)) {
            return;
          }
          setMessages((prev) => [...prev, data]);
          if (!isChatVisibleRef.current) {
            setUnreadCount((count) => count + 1);
          }
        }
      } catch {
        // ignore
      }
    };

    ws.onclose = (event) => {
      wsRef.current = null;
      if (!mountedRef.current) return;
      setConnected(false);
      const msg = closeReasonToMessage(event.code, event.reason);
      setConnectionError(msg);
    };

    ws.onerror = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      setConnectionError((prev) => prev || "Connection failed.");
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [meetingId, jwt]);

  return {
    messages,
    connected,
    connectionError,
    sendMessage,
    unreadCount,
    markChatRead,
  };
}

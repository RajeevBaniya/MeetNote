"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/app/lib/auth/use-auth";
import { getReconnectDelayMs } from "@/app/lib/websocket/reconnect-backoff";

import { fetchWsTicket } from "../auth/ws-ticket";

const buildChatWsUrl = (apiUrl, meetingId, ticket) => {
  const base = (apiUrl || "").replace(/\/$/, "");
  const wsBase = base.replace(/^http:\/\//i, "ws://").replace(/^https:\/\//i, "wss://");
  const t = encodeURIComponent(ticket || "");
  return `${wsBase}/ws/meetings/${meetingId}/chat?ticket=${t}`;
};

const closeReasonToMessage = (code, reason) => {
  const r = (reason || "").toLowerCase();
  if (code === 4408 || r.includes("rate_limit_exceeded")) {
    return "Connection temporarily limited. Please wait a moment.";
  }
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
};

const ASSISTANT_USER_ID = "system:assistant";
const ASSISTANT_DISPLAY_NAME = "Assistant";

const isAssistantMessage = (message) => {
  if (!message) return false;
  const id = typeof message.user_id === "string" ? message.user_id : "";
  const name = typeof message.display_name === "string" ? message.display_name : "";
  return id === ASSISTANT_USER_ID || name === ASSISTANT_DISPLAY_NAME;
};

export const useMeetingChat = (meetingId, jwt, isChatTabVisible = false, onHostChanged) => {
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const wsRef = useRef(null);
  const mountedRef = useRef(true);
  const isChatVisibleRef = useRef(isChatTabVisible);
  const shouldReconnectRef = useRef(true);
  const meetingEndedRef = useRef(false);
  const isConnectingRef = useRef(false);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  isChatVisibleRef.current = isChatTabVisible;
  const { user } = useAuth();
  const currentUserId = user?.id != null ? String(user.id) : null;
  const currentDisplayName =
    (user && typeof user.name === "string" && user.name.trim()) ||
    (user && typeof user.id === "string" && user.id) ||
    "You";

  const markChatRead = useCallback(() => {
    setUnreadCount(0);
  }, []);

  const removeMessageByClientId = useCallback((clientId) => {
    if (!clientId) return;
    setMessages((prev) => prev.filter((m) => m.client_id !== clientId));
  }, []);

  const sendMessage = useCallback(
    (text) => {
      const t = typeof text === "string" ? text.trim() : "";
      if (!t) return;
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        return;
      }

      const clientId =
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

      const optimisticMessage = {
        type: "chat_message",
        user_id: currentUserId || "local_user",
        display_name: currentDisplayName,
        timestamp: new Date().toISOString(),
        text: t,
        optimistic: true,
        failed: false,
        client_id: clientId,
      };

      setMessages((prev) => {
        const updated = [...prev, optimisticMessage];
        return updated.slice(-200);
      });

      try {
        wsRef.current.send(
          JSON.stringify({
            type: "message",
            text: t,
            client_id: clientId,
          }),
        );
      } catch {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.client_id && msg.client_id === clientId
              ? { ...msg, failed: true, optimistic: false }
              : msg,
          ),
        );
      }
    },
    [currentDisplayName, currentUserId]
  );

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      shouldReconnectRef.current = false;
      meetingEndedRef.current = true;
      isConnectingRef.current = false;
      reconnectAttemptRef.current = 0;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!meetingId || !jwt) {
      setConnected(false);
      setReconnecting(false);
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

    shouldReconnectRef.current = true;
    meetingEndedRef.current = false;
    isConnectingRef.current = false;
    reconnectAttemptRef.current = 0;
    setReconnecting(false);

    const scheduleReconnect = (closeEvent) => {
      if (!shouldReconnectRef.current) return;
      if (meetingEndedRef.current) return;
      if (reconnectTimerRef.current) return;
      isConnectingRef.current = false;

      const code = closeEvent?.code;
      const reason = closeEvent?.reason;
      const message = closeReasonToMessage(code, reason);
      setConnectionError(message);

      const isMeetingEnded =
        code === 4400 || (typeof reason === "string" && reason.toLowerCase().includes("meeting ended"));
      const isPermanent =
        code === 4401 || code === 4403 || code === 4400;
      if (isMeetingEnded || isPermanent) {
        meetingEndedRef.current = true;
        shouldReconnectRef.current = false;
        setReconnecting(false);
        return;
      }

      setReconnecting(true);
      const delayMs = getReconnectDelayMs(reconnectAttemptRef.current);
      reconnectAttemptRef.current += 1;
      reconnectTimerRef.current = setTimeout(() => {
        reconnectTimerRef.current = null;
        isConnectingRef.current = false;
        if (!mountedRef.current) return;
        connectWs();
      }, delayMs);
    };

    const connectWs = async () => {
      if (!shouldReconnectRef.current) return;
      if (meetingEndedRef.current) return;
      if (isConnectingRef.current) return;
      if (!meetingId || !jwt) return;

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      isConnectingRef.current = true;

      const ticket = await fetchWsTicket();
      if (!ticket) {
        setConnectionError("Failed to obtain connection ticket. Sign in again.");
        isConnectingRef.current = false;
        scheduleReconnect({ code: 4401, reason: "ticket failed" });
        return;
      }

      if (!shouldReconnectRef.current || meetingEndedRef.current) {
        isConnectingRef.current = false;
        return;
      }

      const url = buildChatWsUrl(apiUrl, meetingId, ticket);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        setConnectionError(null);
        setReconnecting(false);
        reconnectAttemptRef.current = 0;
        isConnectingRef.current = false;
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === "history" && Array.isArray(data.messages)) {
            setMessages(data.messages.slice(-200));
            return;
          }
          if (data.type === "initial_state" && typeof data.current_host_id === "string") {
            try {
              onHostChanged?.(data.current_host_id);
            } catch {}
            return;
          }
          if (data.type === "host_changed" && typeof data.new_host_id === "string") {
            try {
              onHostChanged?.(data.new_host_id);
            } catch {}
            return;
          }
          if (data.type === "chat_message") {
            setMessages((prev) => {
              let replaced = false;
              const withReplacement = prev.map((msg) => {
                if (msg.client_id && data.client_id && msg.client_id === data.client_id) {
                  replaced = true;
                  return {
                    ...msg,
                    ...data,
                    optimistic: false,
                    failed: false,
                  };
                }
                return msg;
              });

              const base = replaced ? withReplacement : [...prev, data];
              return base.slice(-200);
            });
            if (!isChatVisibleRef.current) {
              setUnreadCount((count) => count + 1);
            }
          }
        } catch {}
      };

      ws.onclose = (event) => {
        wsRef.current = null;
        if (!mountedRef.current) return;
        setConnected(false);
        isConnectingRef.current = false;
        scheduleReconnect(event);
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        setConnectionError((prev) => prev || "Connection failed.");
        setReconnecting(true);
        isConnectingRef.current = false;
        scheduleReconnect({ code: 0, reason: "error" });
      };
    };

    connectWs();

    return () => {
      shouldReconnectRef.current = false;
      setReconnecting(false);
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      const ws = wsRef.current;
      if (ws) {
        ws.close();
      }
      wsRef.current = null;
    };
  }, [meetingId, jwt]);

  return {
    messages,
    connected,
    reconnecting,
    connectionError,
    unreadCount,
    sendMessage,
    markChatRead,
    removeMessageByClientId,
  };
};

"use client";

import { useEffect, useState, useRef } from "react";

function buildWsUrl(apiUrl, meetingId, jwt) {
  const base = (apiUrl || "").replace(/\/$/, "");
  const wsBase = base.replace(/^http:\/\//i, "ws://").replace(/^https:\/\//i, "wss://");
  const token = encodeURIComponent(jwt || "");
  return `${wsBase}/ws/meetings/${meetingId}/waiting-room?token=${token}`;
}

export function useWaitingRoom(meetingId, jwt) {
  const [pendingUserIds, setPendingUserIds] = useState([]);
  const [isHost, setIsHost] = useState(false);
  const [disconnected, setDisconnected] = useState(false);
  const wsRef = useRef(null);
  const mountedRef = useRef(true);
  const gotPendingListRef = useRef(false);

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
    if (!meetingId || !jwt) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;

    gotPendingListRef.current = false;
    setIsHost(false);
    setDisconnected(false);
    const url = buildWsUrl(apiUrl, meetingId, jwt);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        if (data.type === "pending_list" && Array.isArray(data.user_ids)) {
          gotPendingListRef.current = true;
          setIsHost(true);
          setPendingUserIds(data.user_ids);
        }
      } catch {
        // ignore
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (!mountedRef.current) return;
      if (gotPendingListRef.current) {
        setDisconnected(true);
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      wsRef.current = null;
    };
  }, [meetingId, jwt]);

  const sendAction = (action, userId) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ action, user_id: userId }));
  };

  return { pendingUserIds, isHost, disconnected, sendAction };
}

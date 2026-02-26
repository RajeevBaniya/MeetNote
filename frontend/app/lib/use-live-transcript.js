"use client";

import { useCallback, useEffect, useRef, useState } from "react";

function buildTranscriptWsUrl(apiUrl, meetingId, jwt) {
  const base = (apiUrl || "").replace(/\/$/, "");
  const wsBase = base
    .replace(/^http:\/\//i, "ws://")
    .replace(/^https:\/\//i, "wss://");
  const token = encodeURIComponent(jwt || "");
  return `${wsBase}/ws/meetings/${meetingId}/transcript?token=${token}`;
}

function parseSegment(seg, index) {
  return {
    id: `history-${index}-${Date.now()}`,
    text: seg.text || "",
    speaker: seg.speaker || seg.speaker_id || "Unknown",
    timestamp: seg.timestamp
      ? new Date(seg.timestamp).toLocaleTimeString()
      : new Date().toLocaleTimeString(),
  };
}

export function useLiveTranscript(meetingId, jwt) {
  const [transcripts, setTranscripts] = useState([]);
  const [connected, setConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const wsRef = useRef(null);
  const mountedRef = useRef(true);

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
      setTranscripts([]);
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      setConnectionError("API URL not configured");
      return;
    }

    setConnectionError(null);
    setTranscripts([]);

    const url = buildTranscriptWsUrl(apiUrl, meetingId, jwt);
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
        if (data.type === "history" && Array.isArray(data.segments)) {
          setTranscripts(data.segments.map(parseSegment));
          return;
        }
        if (data.type === "transcript" && data.segment) {
          const entry = {
            id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
            text: data.segment.text || "",
            speaker:
              data.segment.speaker || data.segment.speaker_id || "Unknown",
            timestamp: data.segment.timestamp
              ? new Date(data.segment.timestamp).toLocaleTimeString()
              : new Date().toLocaleTimeString(),
          };
          setTranscripts((prev) => [...prev, entry]);
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (!mountedRef.current) return;
      setConnected(false);
    };

    ws.onerror = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      setConnectionError((prev) => prev || "Transcript connection failed.");
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [meetingId, jwt]);

  const getSnapshot = useCallback(() => transcripts, [transcripts]);

  return { transcripts, connected, connectionError, getSnapshot };
}

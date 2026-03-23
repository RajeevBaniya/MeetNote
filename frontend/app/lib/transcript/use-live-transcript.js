"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getReconnectDelayMs } from "@/app/lib/websocket/reconnect-backoff";

const buildTranscriptWsUrl = (apiUrl, meetingId, jwt) => {
  const base = (apiUrl || "").replace(/\/$/, "");
  const wsBase = base
    .replace(/^http:\/\//i, "ws://")
    .replace(/^https:\/\//i, "wss://");
  const token = encodeURIComponent(jwt || "");
  return `${wsBase}/ws/meetings/${meetingId}/transcript?token=${token}`;
};

const parseSegment = (seg, fallbackSequence) => {
  const sequenceValue = seg?.sequence;
  const parsedSequence =
    typeof sequenceValue === "number"
      ? sequenceValue
      : sequenceValue != null
        ? Number(sequenceValue)
        : NaN;

  const timestampRaw = seg?.timestamp;
  const speaker = seg?.speaker || seg?.speaker_name || seg?.speaker_id || "Unknown";
  const sequence = Number.isFinite(parsedSequence)
    ? parsedSequence
    : fallbackSequence;

  return {
    id: `seq-${sequence}`,
    sequence,
    text: seg?.text || "",
    speaker,
    timestamp: timestampRaw
      ? new Date(timestampRaw).toLocaleTimeString()
      : new Date().toLocaleTimeString(),
  };
};

const mergeBySequence = (existing, incoming) => {
  const seen = new Set(existing.map((s) => s.sequence));
  const merged = [...existing];

  for (const seg of incoming) {
    if (seen.has(seg.sequence)) continue;
    merged.push(seg);
    seen.add(seg.sequence);
  }

  merged.sort((a, b) => a.sequence - b.sequence);

  return merged;
};

const appendIfNewBySequence = (existing, seg) => {
  if (existing.some((s) => s.sequence === seg.sequence)) {
    return existing;
  }
  const next = [...existing, seg];
  next.sort((a, b) => a.sequence - b.sequence);
  return next;
};

const useLiveTranscript = (meetingId, jwt) => {
  const [transcripts, setTranscripts] = useState([]);
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const wsRef = useRef(null);
  const mountedRef = useRef(true);
  const shouldReconnectRef = useRef(true);
  const meetingEndedRef = useRef(false);
  const isConnectingRef = useRef(false);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const reconnectHistoryNeededRef = useRef(false);
  const hasRestoredFromReconnectRef = useRef(false);
  const fallbackSequenceRef = useRef(-1);

  const toSegment = useCallback((seg) => {
    const fallbackSequence = fallbackSequenceRef.current;
    fallbackSequenceRef.current -= 1;
    return parseSegment(seg, fallbackSequence);
  }, []);

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
    fallbackSequenceRef.current = -1;

    const fetchHistoryAndMerge = async () => {
      try {
        const res = await fetch(
          `${apiUrl}/meetings/${meetingId}/transcript/history?limit=200`,
          {
            headers: {
              Authorization: `Bearer ${jwt}`,
            },
          },
        );
        if (!res.ok) return;
        const data = await res.json();
        if (!data || !Array.isArray(data.segments)) return;
        const parsed = data.segments.map(toSegment);
        setTranscripts((prev) => mergeBySequence(prev, parsed));
        hasRestoredFromReconnectRef.current = true;
      } catch {}
    };

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
      const isMeetingEnded = code === 4400;
      if (isMeetingEnded) {
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

    const connectWs = () => {
      if (!shouldReconnectRef.current) return;
      if (meetingEndedRef.current) return;
      if (isConnectingRef.current) return;
      if (!meetingId || !jwt) return;

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      isConnectingRef.current = true;
      const url = buildTranscriptWsUrl(apiUrl, meetingId, jwt);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        setConnectionError(null);
        setReconnecting(false);
        reconnectAttemptRef.current = 0;

        if (reconnectHistoryNeededRef.current) {
          reconnectHistoryNeededRef.current = false;
          fetchHistoryAndMerge();
        } else {
          hasRestoredFromReconnectRef.current = false;
        }
        isConnectingRef.current = false;
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === "history" && Array.isArray(data.segments)) {
            if (hasRestoredFromReconnectRef.current) {
              return;
            }
            const parsed = data.segments.map(toSegment);
            setTranscripts((prev) => mergeBySequence(prev, parsed));
            return;
          }
          if (data.type === "transcript" && data.segment) {
            const entry = toSegment(data.segment);
            setTranscripts((prev) => appendIfNewBySequence(prev, entry));
          }
        } catch {}
      };

      ws.onclose = (event) => {
        wsRef.current = null;
        if (!mountedRef.current) return;
        setConnected(false);
        reconnectHistoryNeededRef.current = true;
        hasRestoredFromReconnectRef.current = false;
        isConnectingRef.current = false;
        if (event && event.code === 4408) {
          setConnectionError(
            (prev) =>
              prev || "Connection temporarily limited. Please wait a moment.",
          );
        }
        scheduleReconnect(event);
      };

      ws.onerror = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        setConnectionError((prev) => prev || "Transcript connection failed.");
        setReconnecting(true);
        isConnectingRef.current = false;
        scheduleReconnect({ code: 0 });
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
  }, [meetingId, jwt, toSegment]);

  const getSnapshot = useCallback(() => transcripts, [transcripts]);

  return { transcripts, connected, reconnecting, connectionError, getSnapshot };
};

export { useLiveTranscript };

"use client";

import { useEffect, useRef, useState } from "react";
import { getReconnectDelayMs } from "@/app/lib/websocket/reconnect-backoff";
import { fetchWsTicket } from "../auth/ws-ticket";

const useSpeechGateway = (meetingId, jwt, isCallJoined) => {
  const [gatewayStatus, setGatewayStatus] = useState("Offline");
  const wsRef = useRef(null);
  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const isLeavingRef = useRef(false);
  const activeRef = useRef(true);


  const cleanupAll = () => {
    isLeavingRef.current = true;
    setGatewayStatus("Offline");

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    stopRecording();
    closeWebSocket();
  };

  const closeWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      try {
        wsRef.current.close();
      } catch (err) {
        console.error("Error closing speech gateway WS:", err);
      }
      wsRef.current = null;
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      try {
        if (mediaRecorderRef.current.state !== "inactive") {
          mediaRecorderRef.current.stop();
        }
      } catch (err) {
        console.error("Error stopping MediaRecorder:", err);
      }
      mediaRecorderRef.current = null;
    }

    if (streamRef.current) {
      try {
        streamRef.current.getTracks().forEach((track) => track.stop());
      } catch (err) {
        console.error("Error stopping MediaStream tracks:", err);
      }
      streamRef.current = null;
    }
  };

  const connectWebSocket = async () => {
    if (!activeRef.current || isLeavingRef.current) return;

    closeWebSocket();

    const ticket = await fetchWsTicket();
    if (!ticket) {
      loggerWarning("Failed to fetch WS ticket for Speech Gateway");
      triggerReconnect();
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const base = apiUrl.replace(/\/$/, "");
    const wsBase = base.replace(/^http:\/\//i, "ws://").replace(/^https:\/\//i, "wss://");
    const wsUrl = `${wsBase}/ws/meetings/${meetingId}/speech-gateway?ticket=${encodeURIComponent(ticket)}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!activeRef.current || isLeavingRef.current) {
          ws.close();
          return;
        }
        setGatewayStatus("Connected");
        reconnectAttemptRef.current = 0;
        startHeartbeat();
        startAudioCapture();
      };

      ws.onclose = () => {
        if (isLeavingRef.current) return;
        triggerReconnect();
      };

      ws.onerror = (err) => {
        console.error("Speech Gateway WS error:", err);
      };

      ws.onmessage = (event) => {
        // Ready for future event handling
      };
    } catch (err) {
      console.error("Failed to connect Speech Gateway WS:", err);
      triggerReconnect();
    }
  };

  const triggerReconnect = () => {
    if (!activeRef.current || isLeavingRef.current) return;

    setGatewayStatus("Reconnecting");
    stopRecording();
    closeWebSocket();

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }

    const delay = getReconnectDelayMs(reconnectAttemptRef.current);
    reconnectAttemptRef.current += 1;

    reconnectTimerRef.current = setTimeout(() => {
      connectWebSocket();
    }, delay);
  };

  const startHeartbeat = () => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ type: "ping" }));
        } catch (err) {
          console.error("Heartbeat send failed:", err);
        }
      }
    }, 20000);
  };

  const startAudioCapture = async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") return;

    try {
      if (typeof navigator === "undefined" || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        loggerWarning("getUserMedia not supported in this environment");
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      stream.getTracks().forEach((track) => {
        track.onended = () => {
          if (!isLeavingRef.current) {
            console.warn("Microphone stream track ended/revoked");
            setGatewayStatus("Offline");
            stopRecording();
          }
        };
      });

      let mimeType = "audio/webm;codecs=opus";
      if (typeof MediaRecorder !== "undefined") {
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = "audio/webm";
        }
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = "";
        }

        const options = mimeType ? { mimeType } : {};
        const mediaRecorder = new MediaRecorder(stream, options);
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = async (event) => {
          if (event.data && event.data.size > 0) {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              try {
                const arrayBuffer = await event.data.arrayBuffer();
                wsRef.current.send(arrayBuffer);
              } catch (err) {
                console.error("Failed to send audio chunk over WS:", err);
              }
            }
          }
        };

        mediaRecorder.start(250);
      }
    } catch (err) {
      console.error("Microphone access or recorder initialization failed:", err);
      setGatewayStatus("Offline");
    }
  };

  useEffect(() => {
    activeRef.current = true;
    isLeavingRef.current = false;
    reconnectAttemptRef.current = 0;

    if (!meetingId || !jwt || !isCallJoined) {
      setGatewayStatus("Offline");
      return;
    }

    const startGateway = async () => {
      if (!activeRef.current || isLeavingRef.current) return;
      setGatewayStatus("Connecting");
      await connectWebSocket();
    };

    const handleBeforeUnload = () => {
      cleanupAll();
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    startGateway();

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      activeRef.current = false;
      cleanupAll();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingId, jwt, isCallJoined]);

  const loggerWarning = (msg) => {
    console.warn(msg);
  };

  return { gatewayStatus };
};

export default useSpeechGateway;

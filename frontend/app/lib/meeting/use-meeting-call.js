"use client";

import { useEffect, useState, useRef } from "react";
import { useStreamVideoClient } from "@stream-io/video-react-sdk";

import { CALL_TYPE, CLOSED_CAPTIONS_LANGUAGE } from "@/app/lib/meeting/meeting-constants";

const useMeetingCall = (callId, userId, onLeave, onSessionEnded) => {
  const client = useStreamVideoClient();
  const [call, setCall] = useState(null);
  const [error, setError] = useState(null);
  const joinedRef = useRef(false);
  const leavingRef = useRef(false);
  const hasLeftRef = useRef(false);
  const callRef = useRef(null);
  const onSessionEndedRef = useRef(onSessionEnded);
  onSessionEndedRef.current = onSessionEnded;

  useEffect(() => {
    if (!client) return;
    if (joinedRef.current) return;

    joinedRef.current = true;

    const init = async () => {
      try {
        const myCall = client.call(CALL_TYPE, callId);
        await myCall.join({
          create: true,
          data: {
            settings_override: {
              screensharing: {
                enabled: true,
                access_request_enabled: false,
              },
            },
          },
        });

        await myCall.startClosedCaptions({ language: CLOSED_CAPTIONS_LANGUAGE });

        myCall.on("call.session_ended", () => {
          const fn = onSessionEndedRef.current ?? onLeave;
          fn?.();
        });

        callRef.current = myCall;
        setCall(myCall);
      } catch (err) {
        const message =
          (err && typeof err.message === "string" && err.message) ||
          "We couldn't connect to the meeting. Please refresh and try again.";
        setError(message);
      }
    };

    init().catch((err) => {
      console.error("Meeting call init failed:", err);
      setError("We couldn't connect to the meeting. Please refresh and try again.");
    });

    return () => {
      if (hasLeftRef.current) return;
      const c = callRef.current;
      if (c && !leavingRef.current) {
        leavingRef.current = true;
        c.stopClosedCaptions().catch((err) => {
          console.error("Stop closed captions failed:", err);
        });
        c.leave().catch((err) => {
          console.error("Leave call failed:", err);
        });
      }
    };
  }, [client, callId, userId]);

  return { call, error, hasLeftRef };
};

export default useMeetingCall;

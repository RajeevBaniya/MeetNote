"use client";

import { useEffect, useState, useRef } from "react";
import { useStreamVideoClient } from "@stream-io/video-react-sdk";
import { CALL_TYPE, CLOSED_CAPTIONS_LANGUAGE } from "@/app/lib/meeting-constants";

function useMeetingCall(callId, userId, onLeave, onSessionEnded) {
  const client = useStreamVideoClient();
  const [call, setCall] = useState(null);
  const [error, setError] = useState(null);
  const joinedRef = useRef(false);
  const leavingRef = useRef(false);
  const onSessionEndedRef = useRef(onSessionEnded);
  onSessionEndedRef.current = onSessionEnded;

  useEffect(() => {
    if (!client) return;
    if (joinedRef.current) return;

    joinedRef.current = true;

    const init = async () => {
      try {
        const myCall = client.call(CALL_TYPE, callId);
        await myCall.join({ create: true });

        await myCall.startClosedCaptions({ language: CLOSED_CAPTIONS_LANGUAGE });

        myCall.on("call.session_ended", () => {
          const fn = onSessionEndedRef.current ?? onLeave;
          fn?.();
        });

        setCall(myCall);
      } catch (err) {
        setError(err.message);
      }
    };

    init();

    return () => {
      if (call && !leavingRef.current) {
        leavingRef.current = true;
        call.stopClosedCaptions().catch(() => {});
        call.leave().catch(() => {});
      }
    };
  }, [client, callId, userId]);

  return { call, error };
}

export default useMeetingCall;

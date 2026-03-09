"use client";

import { useEffect, useState, useCallback } from "react";
import { useCall } from "@stream-io/video-react-sdk";

const HAND_RAISED = "hand_raised";
const HAND_LOWERED = "hand_lowered";

const useRaisedHands = (currentUserId) => {
  const call = useCall();
  const [raisedSet, setRaisedSet] = useState(() => new Set());

  useEffect(() => {
    if (!call) return;

    const handler = (event) => {
      const payload = event?.custom;
      if (!payload || typeof payload.user_id !== "string") return;
      const uid = payload.user_id;

      if (payload.type === HAND_RAISED) {
        setRaisedSet((prev) => new Set(prev).add(uid));
      } else if (payload.type === HAND_LOWERED) {
        setRaisedSet((prev) => {
          const next = new Set(prev);
          next.delete(uid);
          return next;
        });
      }
    };

    const unsubscribe = call.on("custom", handler);
    return () => {
      if (typeof unsubscribe === "function") unsubscribe();
    };
  }, [call]);

  const raiseHand = useCallback(() => {
    if (!call || !currentUserId) return;
    call.sendCustomEvent({ type: HAND_RAISED, user_id: currentUserId }).catch((err) => {
      console.error("Raise hand event failed:", err);
    });
  }, [call, currentUserId]);

  const lowerHand = useCallback(() => {
    if (!call || !currentUserId) return;
    call.sendCustomEvent({ type: HAND_LOWERED, user_id: currentUserId }).catch((err) => {
      console.error("Lower hand event failed:", err);
    });
  }, [call, currentUserId]);

  const raisedHandUserIds = Array.from(raisedSet);
  const isHandRaised = Boolean(currentUserId && raisedSet.has(currentUserId));

  return {
    raisedHandUserIds,
    raisedHandCount: raisedHandUserIds.length,
    raiseHand,
    lowerHand,
    isHandRaised,
  };
};

export default useRaisedHands;

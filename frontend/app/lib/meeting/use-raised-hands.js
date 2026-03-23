"use client";

import { useCallback, useEffect, useState } from "react";
import { useCall } from "@stream-io/video-react-sdk";

const HAND_RAISED = "hand_raised";
const HAND_LOWERED = "hand_lowered";

const useRaisedHands = (currentUserId) => {
  const call = useCall();
  const [raisedSet, setRaisedSet] = useState(() => new Set());

  useEffect(() => {
    if (!call) return;

    const handler = (event) => {
      if (!event?.custom?.user_id) return;
      const payload = event.custom;
      if (typeof payload.user_id !== "string") return;

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
    if (!call) return;
    if (!currentUserId) return;
    call.sendCustomEvent({ type: HAND_RAISED, user_id: currentUserId }).catch((err) => {
      console.error("Raise hand event failed:", err);
    });
  }, [call, currentUserId]);

  const lowerHand = useCallback(() => {
    if (!call) return;
    if (!currentUserId) return;
    call.sendCustomEvent({ type: HAND_LOWERED, user_id: currentUserId }).catch((err) => {
      console.error("Lower hand event failed:", err);
    });
  }, [call, currentUserId]);

  const lowerHandForUser = useCallback(
    (targetUserId) => {
      if (!call) return;
      if (!targetUserId) return;
      if (
        currentUserId &&
        String(targetUserId) === String(currentUserId)
      ) {
        lowerHand();
        return;
      }
      call.sendCustomEvent({ type: HAND_LOWERED, user_id: targetUserId }).catch((err) => {
        console.error("Lower hand for user failed:", err);
      });
    },
    [call, currentUserId, lowerHand],
  );

  const raisedHandUserIds = Array.from(raisedSet);
  const isHandRaised = Boolean(currentUserId && raisedSet.has(currentUserId));

  return {
    raisedHandUserIds,
    raisedHandCount: raisedHandUserIds.length,
    raiseHand,
    lowerHand,
    lowerHandForUser,
    isHandRaised,
  };
};

export default useRaisedHands;

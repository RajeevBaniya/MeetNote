"use client";

import { useCallback, useEffect, useRef } from "react";

const NEAR_BOTTOM_THRESHOLD_PX = 100;

const useAutoScroll = (triggerKey) => {
  const scrollRef = useRef(null);
  const isNearBottomRef = useRef(true);

  const checkIfNearBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    isNearBottomRef.current = distanceFromBottom <= NEAR_BOTTOM_THRESHOLD_PX;
  }, []);

  const scrollToBottom = useCallback((force = false) => {
    const el = scrollRef.current;
    if (!el) return;
    if (force || isNearBottomRef.current) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener("scroll", checkIfNearBottom, { passive: true });
    return () => {
      el.removeEventListener("scroll", checkIfNearBottom);
    };
  }, [checkIfNearBottom]);

  // triggerKey is a serialized value (e.g. message count) the caller controls.
  // When it changes we scroll if the user is already near the bottom.
  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom, triggerKey]);

  return { scrollRef, scrollToBottom };
};

export default useAutoScroll;

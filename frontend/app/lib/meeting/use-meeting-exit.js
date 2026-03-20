"use client";

import { useCallback, useMemo, useState } from "react";

const getInitialExitState = () => ({ isLeaving: false, isEnding: false });

export const useMeetingExit = () => {
  const [exitState, setExitState] = useState(getInitialExitState);

  const startLeaving = useCallback(() => {
    setExitState({ isLeaving: true, isEnding: false });
  }, []);

  const startEnding = useCallback(() => {
    setExitState({ isLeaving: false, isEnding: true });
  }, []);

  const resetExitState = useCallback(() => {
    setExitState(getInitialExitState());
  }, []);

  const value = useMemo(
    () => ({
      isLeaving: exitState.isLeaving,
      isEnding: exitState.isEnding,
      startLeaving,
      startEnding,
      resetExitState,
    }),
    [exitState.isEnding, exitState.isLeaving, resetExitState, startEnding, startLeaving],
  );

  return value;
};


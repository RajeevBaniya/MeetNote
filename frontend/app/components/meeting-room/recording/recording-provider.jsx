"use client";

import { useEffect, useMemo } from "react";
import { useCall, useCallStateHooks } from "@stream-io/video-react-sdk";

import useLocalRecording from "@/app/lib/recording/use-local-recording";
import { RecordingContext } from "./recording-context";

const RecordingProvider = ({ meetingId, jwt, children }) => {
  const call = useCall();
  const { useLocalParticipant, useHasOngoingScreenShare } = useCallStateHooks();
  const localParticipant = useLocalParticipant();
  const isScreenSharing = useHasOngoingScreenShare();

  const { isRecording, isRecordingAction, elapsed, error, start, stop, stopWithCallback } =
    useLocalRecording({
    call,
    meetingId,
    jwt,
    localParticipant,
    preferScreenShare: true,
    isScreenSharing,
  });

  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (!isRecording) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isRecording]);

  const value = useMemo(() => {
    return {
      isRecording,
      isRecordingAction,
      elapsed,
      error,
      startRecording: start,
      stopRecording: stop,
      stopRecordingWithCallback: stopWithCallback,
    };
  }, [elapsed, error, isRecording, isRecordingAction, start, stop, stopWithCallback]);

  return <RecordingContext.Provider value={value}>{children}</RecordingContext.Provider>;
};

export default RecordingProvider;


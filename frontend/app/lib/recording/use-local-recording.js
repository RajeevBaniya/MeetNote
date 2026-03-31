"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "@/app/lib/ui/use-toast";
import {
  buildRecorderOptions,
  buildRecordingFilename,
  toSeconds,
  triggerDownload,
} from "@/app/lib/recording/recording-utils";
import {
  chooseCaptureStream,
  createCleanupBinding,
  createMetadataClient,
} from "@/app/lib/recording/local-recording-internals";

const useLocalRecording = ({
  call,
  meetingId,
  jwt,
  localParticipant,
  preferScreenShare = false,
  isScreenSharing = false,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isRecordingAction, setIsRecordingAction] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState(null);

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const startedAtRef = useRef(null);
  const recordingIdRef = useRef(null);
  const fileNameRef = useRef(null);
  const stopMetaRef = useRef(null);
  const bindCleanupRef = useRef(null);
  const videoElRef = useRef(null);
  const stoppingRef = useRef(false);
  const intervalRef = useRef(null);
  const onStopCallbackRef = useRef(null);
  const originalTitleRef = useRef(null);
  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setElapsed(0);
  }, []);


  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const recorderOptions = useMemo(() => buildRecorderOptions(), []);
  const cleanupBinding = useMemo(() => createCleanupBinding({ bindCleanupRef, videoElRef }), []);
  const metaClient = useMemo(
    () => createMetadataClient({ apiUrl, meetingId, jwt }),
    [apiUrl, meetingId, jwt],
  );

  const start = useCallback(async () => {
    if (isRecordingAction || isRecording || stoppingRef.current) return;
    if (typeof window === "undefined") return;
    if (!window.MediaRecorder) {
      setError("Recording not supported in this browser.");
      return;
    }
    if (!apiUrl || !meetingId || !jwt) {
      setError("Recording is unavailable.");
      return;
    }
    setIsRecordingAction(true);
    setError(null);
    if (typeof document !== "undefined") {
      if (originalTitleRef.current == null) {
        originalTitleRef.current = document.title;
      }
      document.title = "🔴 Recording...";
    }
    chunksRef.current = [];
    startedAtRef.current = new Date();
    recordingIdRef.current = null;
    fileNameRef.current = buildRecordingFilename({ meetingId });
    stopMetaRef.current = null;

    try {
      const meta = await metaClient.postStart().catch(() => null);
      if (!meta?.recording_id) {
        throw new Error("Failed to start recording.");
      }
      recordingIdRef.current = meta.recording_id;

      const capture = await chooseCaptureStream({
        call,
        localParticipant,
        preferScreenShare,
        isScreenSharing,
        videoElRef,
        bindCleanupRef,
      });
      if (!capture?.stream) {
        throw new Error("No recordable stream available (screen share/camera).");
      }

      const recorder = new MediaRecorder(capture.stream, recorderOptions);
      recorderRef.current = recorder;

      recorder.ondataavailable = (evt) => {
        if (evt?.data && evt.data.size > 0) {
          chunksRef.current = [...chunksRef.current, evt.data];
        }
      };

      recorder.onerror = () => {
        setError("Recording failed.");
      };

      recorder.onstop = async () => {
        const endedAt = stopMetaRef.current?.endedAt || new Date();
        const startedAt = stopMetaRef.current?.startedAt || startedAtRef.current || endedAt;
        const durationSeconds =
          typeof stopMetaRef.current?.durationSeconds === "number"
            ? stopMetaRef.current.durationSeconds
            : toSeconds(endedAt.getTime() - startedAt.getTime());
        const fileName = fileNameRef.current || buildRecordingFilename({ meetingId });

        const blob = new Blob(chunksRef.current, {
          type:
            recorderOptions?.mimeType ||
            (chunksRef.current[0] ? chunksRef.current[0].type : "video/webm"),
        });
        const blobUrl = URL.createObjectURL(blob);
        triggerDownload(blobUrl, fileName);
        toast("Recording saved to your device");
        setTimeout(() => URL.revokeObjectURL(blobUrl), 30_000);

        await metaClient
          .postStop({
            recordingId: recordingIdRef.current,
            fileName,
            startedAt: startedAt.toISOString(),
            endedAt: endedAt.toISOString(),
            durationSeconds,
          })
          .catch(() => {});

        cleanupBinding();
        clearTimer();
        recorderRef.current = null;
        chunksRef.current = [];
        startedAtRef.current = null;
        recordingIdRef.current = null;
        fileNameRef.current = null;
        stopMetaRef.current = null;
        stoppingRef.current = false;
        setIsRecording(false);
        setIsRecordingAction(false);
        if (typeof document !== "undefined" && typeof originalTitleRef.current === "string") {
          document.title = originalTitleRef.current;
        }
        const cb = onStopCallbackRef.current;
        onStopCallbackRef.current = null;
        if (typeof cb === "function") {
          try {
            cb();
          } catch {}
        }
      };

      recorder.start(1000);
      if (intervalRef.current) return;
      intervalRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
      setIsRecording(true);
    } catch (err) {
      cleanupBinding();
      clearTimer();
      if (typeof document !== "undefined" && typeof originalTitleRef.current === "string") {
        document.title = originalTitleRef.current;
      }
      recorderRef.current = null;
      startedAtRef.current = null;
      recordingIdRef.current = null;
      fileNameRef.current = null;
      stopMetaRef.current = null;
      onStopCallbackRef.current = null;
      const msg = typeof err?.message === "string" ? err.message : "Failed to start recording.";
      setError(msg);
    } finally {
      setIsRecordingAction(false);
    }
  }, [cleanupBinding, clearTimer, isRecording, isRecordingAction, apiUrl, meetingId, recorderOptions, jwt, call, localParticipant, preferScreenShare, isScreenSharing, metaClient]);

  const stop = useCallback(() => {
    if (!isRecording || isRecordingAction || stoppingRef.current) return;
    const recorder = recorderRef.current;
    if (!recorder) return;
    stoppingRef.current = true;
    setIsRecordingAction(true);
    try {
      const endedAt = new Date();
      const startedAt = startedAtRef.current || endedAt;
      stopMetaRef.current = {
        startedAt,
        endedAt,
        durationSeconds: toSeconds(endedAt.getTime() - startedAt.getTime()),
      };
      recorder.stop();
    } catch (err) {
      stoppingRef.current = false;
      setIsRecording(false);
      setIsRecordingAction(false);
      clearTimer();
      setError("Failed to stop recording.");
    }
  }, [clearTimer, isRecording, isRecordingAction]);

  const stopWithCallback = useCallback(
    (cb) => {
      onStopCallbackRef.current = typeof cb === "function" ? cb : null;
      stop();
    },
    [stop],
  );

  useEffect(() => {
    return () => {
      try {
        recorderRef.current?.stop?.();
      } catch {}
      clearTimer();
      cleanupBinding();
      if (typeof document !== "undefined" && typeof originalTitleRef.current === "string") {
        document.title = originalTitleRef.current;
      }
    };
  }, [cleanupBinding, clearTimer]);

  return { isRecording, isRecordingAction, elapsed, error, start, stop, stopWithCallback };
};

export default useLocalRecording;

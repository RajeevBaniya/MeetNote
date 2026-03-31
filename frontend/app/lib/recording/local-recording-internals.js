"use client";

import { isScreenSharePublisher } from "@/app/lib/screenshare/screen-share";
import {
  captureStreamFromVideoElement,
  createHiddenVideoElement,
  hasActiveVideoTrack,
} from "@/app/lib/recording/recording-utils";

const createCleanupBinding = ({ bindCleanupRef, videoElRef }) => {
  return () => {
    const cleanup = bindCleanupRef.current;
    bindCleanupRef.current = null;
    if (typeof cleanup === "function") {
      try {
        cleanup();
      } catch {}
    }
    const videoEl = videoElRef.current;
    videoElRef.current = null;
    if (videoEl && videoEl.parentNode) {
      videoEl.parentNode.removeChild(videoEl);
    }
  };
};

const createMetadataClient = ({ apiUrl, meetingId, jwt }) => {
  const postStart = async () => {
    if (!apiUrl || !meetingId || !jwt) return null;
    const res = await fetch(`${apiUrl}/meetings/${meetingId}/recording/start`, {
      method: "POST",
      headers: { Authorization: `Bearer ${jwt}` },
    });
    if (!res.ok) return null;
    const data = await res.json().catch(() => null);
    if (!data || typeof data.recording_id !== "string") return null;
    return data;
  };

  const postStop = async ({ recordingId, fileName, startedAt, endedAt, durationSeconds }) => {
    if (!apiUrl || !meetingId || !jwt) return;
    if (!recordingId) return;
    await fetch(`${apiUrl}/meetings/${meetingId}/recording/stop`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${jwt}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        recording_id: recordingId,
        file_name: fileName,
        started_at: startedAt,
        ended_at: endedAt,
        duration_seconds: durationSeconds,
      }),
    }).catch(() => {});
  };

  return { postStart, postStop };
};

const bindTrackToVideo = async ({ call, sessionId, trackName, videoElRef, bindCleanupRef }) => {
  if (!call || !sessionId) return null;
  const videoEl = createHiddenVideoElement();
  document.body.appendChild(videoEl);
  videoElRef.current = videoEl;
  const cleanup = await call.bindVideoElement(videoEl, sessionId, trackName);
  bindCleanupRef.current = cleanup;
  try {
    await videoEl.play();
  } catch {}
  const stream = captureStreamFromVideoElement(videoEl);
  if (!hasActiveVideoTrack(stream)) return null;
  return stream;
};

const chooseCaptureStream = async ({
  call,
  localParticipant,
  preferScreenShare,
  isScreenSharing,
  videoElRef,
  bindCleanupRef,
}) => {
  const sessionId = localParticipant?.sessionId;
  const wantsScreen = Boolean(
    preferScreenShare && isScreenSharing && isScreenSharePublisher(localParticipant),
  );

  if (wantsScreen) {
    const screen = await bindTrackToVideo({
      call,
      sessionId,
      trackName: "screenShareTrack",
      videoElRef,
      bindCleanupRef,
    });
    if (screen) return { stream: screen, source: "screen" };
  }

  const cam = await bindTrackToVideo({
    call,
    sessionId,
    trackName: "videoTrack",
    videoElRef,
    bindCleanupRef,
  });
  if (cam) return { stream: cam, source: "camera" };
  return null;
};

export { chooseCaptureStream, createCleanupBinding, createMetadataClient };


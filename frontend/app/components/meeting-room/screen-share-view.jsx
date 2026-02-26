"use client";

import { useEffect, useMemo, useRef } from "react";
import { useCall, useCallStateHooks } from "@stream-io/video-react-sdk";

const SCREEN_SHARE_TRACK_NAMES = ["screenShareTrack", "screen", "SCREEN_SHARE"];
const SCREEN_SHARE_TRACK_IDS = [3];

export function isScreenSharePublisher(participant) {
  if (!participant) return false;
  if (participant.screenShareStream) return true;
  const tracks = participant.publishedTracks || [];
  const hasTrackByName = tracks.some((t) => {
    if (typeof t === "string") return SCREEN_SHARE_TRACK_NAMES.includes(t);
    if (typeof t === "number") return SCREEN_SHARE_TRACK_IDS.includes(t);
    return false;
  });
  return hasTrackByName;
}

const ScreenShareView = () => {
  const call = useCall();
  const { useParticipants, useHasOngoingScreenShare } = useCallStateHooks();
  const participants = useParticipants() || [];
  const hasOngoingScreenShare = useHasOngoingScreenShare();
  const videoRef = useRef(null);

  const screenSharingParticipant = useMemo(
    () => participants.find(isScreenSharePublisher),
    [participants]
  );

  useEffect(() => {
    const videoElement = videoRef.current;
    if (!call || !videoElement || !screenSharingParticipant) return;

    let cleanup = null;
    const sessionId = screenSharingParticipant.sessionId;

    const bindVideo = async () => {
      try {
        cleanup = await call.bindVideoElement(
          videoElement,
          sessionId,
          "screenShareTrack"
        );
      } catch (err) {
        console.error("Failed to bind screen share video:", err);
      }
    };

    bindVideo();

    return () => {
      if (cleanup) {
        cleanup();
      }
    };
  }, [call, screenSharingParticipant?.sessionId]);

  if (!hasOngoingScreenShare || participants.length === 0) {
    return (
      <div className="absolute inset-0 w-full h-full bg-[#0a0a0f] flex items-center justify-center">
        <p className="text-slate-500 text-sm">No screen share active</p>
      </div>
    );
  }

  if (!screenSharingParticipant) {
    return (
      <div className="absolute inset-0 w-full h-full bg-[#0a0a0f] flex items-center justify-center">
        <p className="text-slate-500 text-sm">Waiting for screen share...</p>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 w-full h-full bg-[#0a0a0f] overflow-hidden">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={false}
        className="w-full h-full object-contain"
      />
    </div>
  );
};

export default ScreenShareView;
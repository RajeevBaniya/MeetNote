"use client";

const SCREEN_SHARE_TRACK_NAMES = ["screenShareTrack", "screen", "SCREEN_SHARE"];
const SCREEN_SHARE_TRACK_IDS = [3];

export const isScreenSharePublisher = (participant) => {
  if (!participant) return false;
  if (participant.screenShareStream) return true;
  const tracks = participant.publishedTracks || [];
  const hasTrackByName = tracks.some((t) => {
    if (typeof t === "string") return SCREEN_SHARE_TRACK_NAMES.includes(t);
    if (typeof t === "number") return SCREEN_SHARE_TRACK_IDS.includes(t);
    return false;
  });
  return hasTrackByName;
};

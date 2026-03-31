"use client";

const safeFilename = (name) => {
  const raw = typeof name === "string" ? name : "";
  const trimmed = raw.trim() || "recording.webm";
  const cleaned = trimmed.replace(/[^a-zA-Z0-9._-]+/g, "_");
  const capped = cleaned.length > 160 ? cleaned.slice(0, 160) : cleaned;
  return capped || "recording.webm";
};

const buildRecordingFilename = ({ meetingId }) => {
  const id = meetingId ? String(meetingId) : "meeting";
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  return safeFilename(`recording-${id}-${stamp}.webm`);
};

const triggerDownload = (blobUrl, filename) => {
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = safeFilename(filename);
  a.rel = "noopener noreferrer";
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
};

const createHiddenVideoElement = () => {
  const el = document.createElement("video");
  el.muted = true;
  el.playsInline = true;
  el.style.position = "fixed";
  el.style.left = "-99999px";
  el.style.top = "0";
  el.style.width = "1px";
  el.style.height = "1px";
  return el;
};

const captureStreamFromVideoElement = (videoEl) => {
  if (!videoEl) return null;
  if (typeof videoEl.captureStream === "function") return videoEl.captureStream();
  if (typeof videoEl.mozCaptureStream === "function") return videoEl.mozCaptureStream();
  return null;
};

const hasActiveVideoTrack = (stream) => {
  if (!stream || typeof stream.getVideoTracks !== "function") return false;
  const tracks = stream.getVideoTracks();
  return Array.isArray(tracks) && tracks.length > 0;
};

const toSeconds = (ms) => Math.max(0, Math.round(ms / 1000));

const buildRecorderOptions = () => {
  const options = { mimeType: "video/webm;codecs=vp8,opus" };
  if (typeof window === "undefined") return options;
  if (!window.MediaRecorder || typeof window.MediaRecorder.isTypeSupported !== "function") {
    return options;
  }
  if (!MediaRecorder.isTypeSupported(options.mimeType)) {
    delete options.mimeType;
  }
  return options;
};

export {
  buildRecorderOptions,
  buildRecordingFilename,
  captureStreamFromVideoElement,
  createHiddenVideoElement,
  hasActiveVideoTrack,
  safeFilename,
  toSeconds,
  triggerDownload,
};


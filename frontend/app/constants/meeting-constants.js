/**
 * Meeting Application Constants
 * 
 * Centralized constants for the meeting application.
 * This ensures consistency and makes configuration changes easier.
 */

export const PARTICIPANT_CONSTANTS = {
  ASSISTANT_USER_ID: "meeting-assistant-bot",
  ASSISTANT_NAME: "Assistant",
  ASSISTANT_NAME_VARIANTS: ["assistant", "meeting-assistant-bot"],
};

export const LAYOUT_CONSTANTS = {
  TRANSCRIPT_PANEL_WIDTH: "320px",
  PARTICIPANT_SIDEBAR_WIDTH: "224px", // w-56
  COMPACT_TILE_HEIGHT: "128px", // h-32
  GRID_GAP_NORMAL: "12px", // gap-3
  GRID_GAP_COMPACT: "8px", // gap-2
  PADDING_NORMAL: "16px", // p-4
  PADDING_COMPACT: "8px", // p-2
};

export const GRID_LAYOUT_BREAKPOINTS = {
  SINGLE: 1,
  TWO: 2,
  FOUR: 4,
  SIX: 6,
  NINE: 9,
  TWELVE: 12,
  SIXTEEN: 16,
};

export const TRIGGER_PHRASES = [
  "hey assistant",
  "hi assistant",
  "hello assistant",
];

export const PERMISSION_RESPONSES = {
  GRANTED: ["yes", "yeah", "yep", "sure", "okay", "ok", "go ahead"],
  DENIED: ["no", "nope", "nah", "don't", "dont"],
};

export const CALL_TYPE = "default";

export const CLOSED_CAPTIONS_LANGUAGE = "en";

export const ERROR_MESSAGES = {
  CALL_INIT_FAILED: "Failed to initialize call",
  CALL_JOIN_FAILED: "Failed to join call",
  CLOSED_CAPTIONS_FAILED: "Failed to start closed captions",
  CHAT_CHANNEL_FAILED: "Failed to initialize chat channel",
  AGENT_RESPONSE_FAILED: "Failed to generate agent response",
};

export const LOG_LEVELS = {
  INFO: "INFO",
  ERROR: "ERROR",
  WARN: "WARN",
  DEBUG: "DEBUG",
};
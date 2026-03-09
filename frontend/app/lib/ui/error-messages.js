"use client";

const DEFAULT_MESSAGES = {
  rate_limit_exceeded: "Too many attempts. Please wait a moment and try again.",
  unauthorized: "Your session expired. Please sign in again.",
  network_error: "Connection problem. Please check your internet connection.",
  unknown: "Something went wrong. Please try again.",
};

const asLower = (value) =>
  typeof value === "string" ? value.trim().toLowerCase() : "";

const extractCode = (error) => {
  if (!error) return null;

  if (typeof error === "string") {
    const lower = asLower(error);
    if (lower.includes("rate limit") || lower.includes("too many requests")) {
      return "rate_limit_exceeded";
    }
    if (lower.includes("unauthorized") || lower.includes("session")) {
      return "unauthorized";
    }
    if (lower.includes("network") || lower.includes("connection")) {
      return "network_error";
    }
    return null;
  }

  if (typeof error === "object") {
    if (typeof error.code === "string" && error.code.trim() !== "") {
      return error.code.trim();
    }
    if (typeof error.errorCode === "string" && error.errorCode.trim() !== "") {
      return error.errorCode.trim();
    }
    if (error.status === 429) return "rate_limit_exceeded";
    if (error.status === 401 || error.status === 403) return "unauthorized";
  }

  return null;
};

export const isRateLimitError = (error) => {
  const code = extractCode(error);
  if (code === "rate_limit_exceeded") return true;

  if (typeof error === "object" && error && error.status === 429) {
    return true;
  }

  const text = asLower(
    typeof error === "string" ? error : error && error.message,
  );
  return (
    text.includes("too many requests") ||
    text.includes("rate limit") ||
    text.includes("rate_limit_exceeded")
  );
};

export const getErrorMessage = (error) => {
  if (!error) return DEFAULT_MESSAGES.unknown;

  if (typeof error === "string") {
    return error;
  }

  if (typeof error === "object") {
    if (typeof error.message === "string" && error.message.trim() !== "") {
      return error.message.trim();
    }
    const code = extractCode(error);
    if (code && DEFAULT_MESSAGES[code]) {
      return DEFAULT_MESSAGES[code];
    }
  }

  return DEFAULT_MESSAGES.unknown;
};


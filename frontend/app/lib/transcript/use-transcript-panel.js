"use client";

import { useState, useCallback } from "react";

const useTranscriptPanel = () => {
  const [isTranscriptOpen, setIsTranscriptOpen] = useState(false);

  const toggleTranscript = useCallback(() => {
    setIsTranscriptOpen((prev) => !prev);
  }, []);

  const closeTranscript = useCallback(() => {
    setIsTranscriptOpen(false);
  }, []);

  return { isTranscriptOpen, toggleTranscript, closeTranscript };
};

export { useTranscriptPanel };

"use client";

import { createContext, useContext } from "react";

const RecordingContext = createContext(null);

const useRecording = () => {
  const ctx = useContext(RecordingContext);
  return ctx;
};

export { RecordingContext, useRecording };


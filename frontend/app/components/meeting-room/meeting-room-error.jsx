"use client";

import React from "react";

const MeetingRoomError = ({ error }) => {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
      <p className="text-slate-300">Error: {error}</p>
    </div>
  );
};

export default MeetingRoomError;
"use client";

const MeetingRoomError = ({ error }) => {
  return (
    <div className="flex items-center justify-center min-h-screen text-white">
      <p>Error: {error}</p>
    </div>
  );
};

export default MeetingRoomError;
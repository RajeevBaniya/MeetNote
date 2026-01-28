"use client";

const MeetingRoomLoading = () => {
  return (
    <div className="flex items-center justify-center min-h-screen text-white">
      <div className="text-center">
        <div className="animate-spin h-16 w-16 border-t-4 border-blue-500 mx-auto rounded-full" />
        <p className="mt-4 text-lg">Loading meeting…</p>
      </div>
    </div>
  );
};

export default MeetingRoomLoading;
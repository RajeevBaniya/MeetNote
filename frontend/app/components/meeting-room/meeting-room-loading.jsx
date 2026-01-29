"use client";

const MeetingRoomLoading = () => {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
      <div className="text-center">
        <div className="animate-spin h-16 w-16 border-t-4 border-emerald-500 mx-auto rounded-full" />
        <p className="mt-4 text-lg text-slate-300">Loading meeting…</p>
      </div>
    </div>
  );
};

export default MeetingRoomLoading;
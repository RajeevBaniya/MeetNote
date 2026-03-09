"use client";

import { StreamVideo } from "@stream-io/video-react-sdk";

import { useStreamClients } from "@/app/lib/stream/use-stream-clients";

const API_KEY = process.env.NEXT_PUBLIC_STREAM_API_KEY;

const StreamProvider = ({ children, user, getToken }) => {
  const { videoClient } = useStreamClients({ apiKey: API_KEY, user, getToken });

  if (!videoClient) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-[#020617] text-slate-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-emerald-500 mx-auto" />
          <p className="text-slate-300 text-xl font-semibold mt-6">Connecting...</p>
        </div>
      </div>
    );
  }

  return <StreamVideo client={videoClient}>{children}</StreamVideo>;
};

export default StreamProvider;

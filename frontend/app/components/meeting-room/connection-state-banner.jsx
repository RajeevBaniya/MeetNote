"use client";

import { useCallStateHooks } from "@stream-io/video-react-sdk";
import { CallingState } from "@stream-io/video-client";

function ConnectionStateBanner() {
  const { useCallCallingState } = useCallStateHooks();
  const callingState = useCallCallingState();

  if (callingState === CallingState.RECONNECTING || callingState === CallingState.MIGRATING) {
    return (
      <div className="absolute top-0 left-0 right-0 z-40 flex justify-center py-2 px-4 bg-amber-600/90 text-white text-sm font-medium">
        Reconnecting…
      </div>
    );
  }

  if (callingState === CallingState.OFFLINE) {
    return (
      <div className="absolute top-0 left-0 right-0 z-40 flex justify-center py-2 px-4 bg-amber-600/90 text-white text-sm font-medium">
        Connection lost, retrying…
      </div>
    );
  }

  if (callingState === CallingState.RECONNECTING_FAILED) {
    return (
      <div className="absolute top-0 left-0 right-0 z-40 flex justify-center py-2 px-4 bg-red-600/90 text-white text-sm font-medium">
        Connection failed. Check your network and refresh to rejoin.
      </div>
    );
  }

  return null;
}

export default ConnectionStateBanner;

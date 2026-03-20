import { useState, useEffect, useRef } from "react";
import {
  StreamVideoClient,
  videoLoggerSystem,
  logToConsole,
} from "@stream-io/video-react-sdk";

const isPermissionDeniedError = (err) => {
  if (!err || typeof err !== "object") return false;
  const name = err.name || err?.cause?.name || "";
  const msg = String(err.message || err?.cause?.message || "").toLowerCase();
  return (
    name === "NotAllowedError" || msg.includes("permission denied by user")
  );
};

const configureDevicesLogger = () => {
  if (typeof window === "undefined") return;
  try {
    videoLoggerSystem.configureLoggers({
      devices: {
        sink(logLevel, message, ...rest) {
          if (
            logLevel === "error" &&
            typeof message === "string" &&
            message.includes("Failed to get screen share stream") &&
            rest.length > 0
          ) {
            if (isPermissionDeniedError(rest[0])) return;
          }
          logToConsole(logLevel, message, ...rest);
        },
      },
    });
  } catch (err) {
    console.error("Configure devices logger failed:", err);
  }
};

configureDevicesLogger();

export const useStreamClients = ({ apiKey, user, getToken }) => {
  const [videoClient, setVideoClient] = useState(null);
  const clientRef = useRef(null);
  const getTokenRef = useRef(getToken);

  useEffect(() => {
    getTokenRef.current = getToken;
  });

  useEffect(() => {
    if (!user || !apiKey || typeof getToken !== "function") return;

    let isMounted = true;

    const tokenProvider = () => {
      const t = getTokenRef.current ? getTokenRef.current() : null;
      return Promise.resolve(t != null ? t : "");
    };

    const initClient = () => {
      try {
        const myVideoClient = new StreamVideoClient({
          apiKey,
          user,
          tokenProvider,
        });
        clientRef.current = myVideoClient;
        if (isMounted) setVideoClient(myVideoClient);
      } catch (err) {
        console.error("Client initialization error:", err);
      }
    };

    initClient();

    return () => {
      isMounted = false;
      const client = clientRef.current;
      clientRef.current = null;
      if (client) client.disconnectUser().catch((err) => {
        console.error("Disconnect user failed:", err);
      });
    };
  }, [apiKey, user, getToken]);

  return { videoClient };
};

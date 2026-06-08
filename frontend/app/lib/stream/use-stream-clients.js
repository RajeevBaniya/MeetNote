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
    let clientInstance = null;

    const tokenProvider = () => {
      const t = getTokenRef.current ? getTokenRef.current() : null;
      return Promise.resolve(t != null ? t : "");
    };

    const initClient = async () => {
      console.log("[Stream] Client creation start...");
      try {
        const myVideoClient = new StreamVideoClient({
          apiKey,
        });
        clientInstance = myVideoClient;
        console.log("[Stream] Client instantiated successfully.");

        console.log("[Stream] connectUser start for user:", user.id);
        const token = await tokenProvider();
        await myVideoClient.connectUser(user, token);
        console.log("[Stream] connectUser success for user:", user.id);

        if (!isMounted) {
          console.log("[Stream] Component unmounted during connection. Disconnecting...");
          myVideoClient.disconnectUser().catch((err) => {
            console.error("[Stream] Disconnect user failed during clean up:", err);
          });
          return;
        }

        clientRef.current = myVideoClient;
        setVideoClient(myVideoClient);
      } catch (err) {
        console.error("[Stream] connectUser failure:", err);
      }
    };

    initClient();

    return () => {
      isMounted = false;
      const client = clientRef.current || clientInstance;
      clientRef.current = null;
      if (client) {
        console.log("[Stream] disconnectUser called for cleanup.");
        client.disconnectUser().catch((err) => {
          console.error("[Stream] Disconnect user failed during unmount cleanup:", err);
        });
      }
    };
  }, [apiKey, user, getToken]);

  return { videoClient };
};

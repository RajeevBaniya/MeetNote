import { useState, useEffect, useRef } from "react";
import { StreamVideoClient } from "@stream-io/video-react-sdk";

export function useStreamClients({ apiKey, user, getToken }) {
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
      if (client) client.disconnectUser().catch(() => {});
    };
  }, [apiKey, user, getToken]);

  return { videoClient };
}

import { useState, useEffect, useRef } from "react";
import { StreamVideoClient } from "@stream-io/video-react-sdk";

export function useStreamClients({ apiKey, user, token }) {
  const [videoClient, setVideoClient] = useState(null);
  const clientRef = useRef(null);

  useEffect(() => {
    if (!user || !token || !apiKey) return;

    let isMounted = true;

    const initClient = async () => {
      try {
        const tokenProvider = () => Promise.resolve(token);
        const myVideoClient = new StreamVideoClient({
          apiKey,
          user,
          tokenProvider,
        });

        clientRef.current = myVideoClient;
        if (isMounted) {
          setVideoClient(myVideoClient);
        }
      } catch (error) {
        console.error("Client initialization error:", error);
      }
    };

    initClient();

    return () => {
      isMounted = false;
      const client = clientRef.current;
      clientRef.current = null;
      if (client) {
        client.disconnectUser().catch(console.error);
      }
    };
  }, [apiKey, user, token]);

  return { videoClient };
}

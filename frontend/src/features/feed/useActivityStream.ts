import { useEffect, useRef, useState } from "react";

import { openActivityStream, type Activity } from "../../api";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30_000;

export interface ActivityStream {
  /** Items pushed since load, newest first. */
  inserted: Activity[];
  /** Announced politely, so a new card is heard as well as seen. */
  announcement: string;
  /** Set while the stream is down, for the reconnecting warning bar. */
  paused: boolean;
}

/**
 * Subscribes to `activity.created` and reconnects with bounded backoff
 * (api-contract, `GET /activities/stream`).
 */
export function useActivityStream(): ActivityStream {
  const [inserted, setInserted] = useState<Activity[]>([]);
  const [announcement, setAnnouncement] = useState("");
  const [paused, setPaused] = useState(false);
  const attempt = useRef(0);

  useEffect(() => {
    let source: EventSource | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let closed = false;

    const connect = () => {
      source = openActivityStream();

      source.addEventListener("activity.created", (raw) => {
        const activity = JSON.parse((raw as MessageEvent<string>).data) as Activity;
        attempt.current = 0;
        setPaused(false);
        setInserted((current) => [activity, ...current]);
        setAnnouncement(`New competitor activity: ${activity.title}`);
      });

      source.onopen = () => {
        attempt.current = 0;
        setPaused(false);
      };

      source.onerror = () => {
        source?.close();
        if (closed) return;
        setPaused(true);
        const delay = Math.min(RECONNECT_BASE_MS * 2 ** attempt.current, RECONNECT_MAX_MS);
        attempt.current += 1;
        retry = setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      source?.close();
    };
  }, []);

  return { inserted, announcement, paused };
}

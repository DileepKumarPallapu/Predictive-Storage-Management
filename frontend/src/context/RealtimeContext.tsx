import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, authStorage, getWebSocketUrl, invalidateApiCache } from "../api/client";

export type ConnectionStatus = "LIVE" | "RECONNECTING" | "DISCONNECTED";

export interface RealtimeEvent {
  event_id?: string;
  seq_id?: number;
  event_type: string;
  event_version?: number;
  organization_id?: string;
  actor_user_id?: string;
  actor_username?: string;
  actor_role?: string;
  resource_type?: string;
  resource_id?: string;
  event_timestamp?: string;
  entity_version?: number;
  changed_fields?: string[];
  relevant_safe_payload?: Record<string, any>;
}

interface RealtimeContextValue {
  connectionStatus: ConnectionStatus;
  lastUpdatedAt: string | null;
  lastSeqId: number;
  notifications: any[];
  unreadCount: number;
  onlineUsers: any[];
  recentEvents: RealtimeEvent[];
  refreshNotifications: () => Promise<void>;
  refreshPresence: () => Promise<void>;
  markNotificationRead: (id: string) => Promise<void>;
  markAllNotificationsRead: () => Promise<void>;
}

const RealtimeContext = createContext<RealtimeContextValue>({
  connectionStatus: "DISCONNECTED",
  lastUpdatedAt: null,
  lastSeqId: 0,
  notifications: [],
  unreadCount: 0,
  onlineUsers: [],
  recentEvents: [],
  refreshNotifications: async () => {},
  refreshPresence: async () => {},
  markNotificationRead: async () => {},
  markAllNotificationsRead: async () => {},
});

function invalidateForEvent(evt: RealtimeEvent) {
  const et = evt.event_type || "";
  if (et.startsWith("storage.") || et.startsWith("telemetry.") || et.startsWith("ingestion.")) {
    invalidateApiCache("/devices");
    invalidateApiCache("/storage");
    invalidateApiCache("/overview");
    invalidateApiCache("/operator/dashboard");
    invalidateApiCache("/telemetry");
    invalidateApiCache("/ingestion");
    invalidateApiCache("/data-quality");
  } else if (et.startsWith("model.") || et.startsWith("forecast.") || et.startsWith("risk.")) {
    invalidateApiCache("/v2/");
    invalidateApiCache("/models");
    invalidateApiCache("/forecasts");
    invalidateApiCache("/risk");
    invalidateApiCache("/overview");
    invalidateApiCache("/operator/dashboard");
  } else if (et.startsWith("alert.")) {
    invalidateApiCache("/alerts");
    invalidateApiCache("/overview");
    invalidateApiCache("/operator/dashboard");
  } else if (et.startsWith("scenario.")) {
    invalidateApiCache("/scenarios");
    invalidateApiCache("/digital-twin");
  } else if (et.startsWith("recommendation.") || et.startsWith("approval.")) {
    invalidateApiCache("/recommendations");
    invalidateApiCache("/overview");
    invalidateApiCache("/operator/dashboard");
  } else if (et.startsWith("task.")) {
    invalidateApiCache("/tasks");
    invalidateApiCache("/operator/dashboard");
  } else if (et.startsWith("settings.") || et.startsWith("user.") || et.startsWith("permissions.")) {
    invalidateApiCache("/settings");
    invalidateApiCache("/users");
    invalidateApiCache("/auth");
  } else if (et.startsWith("action.") || et.startsWith("connector.")) {
    invalidateApiCache("/control-plane");
  }
}

export const RealtimeProvider: React.FC<{
  authenticated: boolean;
  currentRoute: string;
  children: React.ReactNode;
}> = ({ authenticated, currentRoute, children }) => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("DISCONNECTED");
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);
  const [lastSeqId, setLastSeqId] = useState<number>(0);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [onlineUsers, setOnlineUsers] = useState<any[]>([]);
  const [recentEvents, setRecentEvents] = useState<RealtimeEvent[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const seqRef = useRef<number>(0);
  const retryRef = useRef<number>(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const heartbeatTimerRef = useRef<number | null>(null);
  const routeRef = useRef<string>(currentRoute);
  routeRef.current = currentRoute;

  const refreshNotifications = useCallback(async () => {
    if (!authenticated) return;
    try {
      const res = await api.listNotifications(false);
      setNotifications(res.notifications || []);
      setUnreadCount(res.unread_count || 0);
    } catch {
      // ignore transient error
    }
  }, [authenticated]);

  const refreshPresence = useCallback(async () => {
    if (!authenticated) return;
    try {
      const res = await api.getLivePresence();
      setOnlineUsers(res.users || []);
    } catch {
      // ignore transient error
    }
  }, [authenticated]);

  const markNotificationRead = useCallback(async (id: string) => {
    await api.markNotificationRead(id);
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    setUnreadCount((c) => Math.max(0, c - 1));
  }, []);

  const markAllNotificationsRead = useCallback(async () => {
    await api.markAllNotificationsRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  }, []);

  useEffect(() => {
    if (!authenticated) {
      setConnectionStatus("DISCONNECTED");
      setNotifications([]);
      setUnreadCount(0);
      setOnlineUsers([]);
      if (wsRef.current) {
        wsRef.current.close(1000, "Logged out");
        wsRef.current = null;
      }
      return;
    }

    let disposed = false;

    const handleIncomingEvent = (evt: RealtimeEvent) => {
      if (!evt || !evt.event_type) return;
      if (evt.event_type === "system.pong") return;

      if (evt.event_type === "system.connected") {
        if (typeof (evt as any).current_seq === "number" && (evt as any).current_seq > seqRef.current) {
          seqRef.current = (evt as any).current_seq;
          setLastSeqId(seqRef.current);
        }
        setLastUpdatedAt(evt.event_timestamp || new Date().toISOString());
        return;
      }

      if (evt.event_type === "auth.connection_terminated" || evt.event_type === "auth.session_revoked") {
        authStorage.clearToken();
        window.dispatchEvent(new CustomEvent("aegisstor:auth-expired", { detail: { reason: (evt as any).reason } }));
        return;
      }

      if (typeof evt.seq_id === "number" && evt.seq_id > seqRef.current) {
        seqRef.current = evt.seq_id;
        setLastSeqId(evt.seq_id);
      }
      setLastUpdatedAt(evt.event_timestamp || new Date().toISOString());

      invalidateForEvent(evt);

      if (!evt.event_type.startsWith("presence.")) {
        setRecentEvents((prev) => [evt, ...prev].slice(0, 50));
      } else {
        refreshPresence();
      }

      if (
        evt.event_type.startsWith("task.") ||
        evt.event_type.startsWith("alert.") ||
        evt.event_type.startsWith("approval.") ||
        evt.event_type.startsWith("notification.")
      ) {
        refreshNotifications();
      }

      window.dispatchEvent(new CustomEvent("aegisstor:realtime-event", { detail: evt }));
    };

    const connect = () => {
      if (disposed) return;
      setConnectionStatus(retryRef.current > 0 ? "RECONNECTING" : "DISCONNECTED");

      const token = authStorage.getToken();
      const wsUrl = getWebSocketUrl(token, seqRef.current > 0 ? seqRef.current : undefined, routeRef.current);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (disposed) return;
        retryRef.current = 0;
        setConnectionStatus("LIVE");
        setLastUpdatedAt(new Date().toISOString());
        refreshNotifications();
        refreshPresence();

        if (heartbeatTimerRef.current) window.clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping", route: routeRef.current }));
          }
        }, 25000);
      };

      ws.onmessage = (message) => {
        try {
          const parsed = JSON.parse(message.data);
          handleIncomingEvent(parsed);
        } catch {
          // ignore malformed frames
        }
      };

      ws.onclose = (ev) => {
        if (heartbeatTimerRef.current) {
          window.clearInterval(heartbeatTimerRef.current);
          heartbeatTimerRef.current = null;
        }
        if (disposed) return;
        if (ev.code === 4001 || ev.code === 4003) {
          setConnectionStatus("DISCONNECTED");
          authStorage.clearToken();
          window.dispatchEvent(new CustomEvent("aegisstor:auth-expired", { detail: { reason: ev.reason } }));
          return;
        }
        setConnectionStatus("RECONNECTING");
        const delayMs = Math.min(15000, 1000 * Math.pow(2, retryRef.current));
        retryRef.current += 1;
        reconnectTimerRef.current = window.setTimeout(connect, delayMs);
      };

      ws.onerror = () => {
        // onclose will trigger backoff reconnect
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      if (heartbeatTimerRef.current) window.clearInterval(heartbeatTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close(1000, "Provider unmount");
        wsRef.current = null;
      }
    };
  }, [authenticated, refreshNotifications, refreshPresence]);

  // Update presence route when user navigates
  useEffect(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "presence_route", route: currentRoute }));
    }
  }, [currentRoute]);

  return (
    <RealtimeContext.Provider
      value={{
        connectionStatus,
        lastUpdatedAt,
        lastSeqId,
        notifications,
        unreadCount,
        onlineUsers,
        recentEvents,
        refreshNotifications,
        refreshPresence,
        markNotificationRead,
        markAllNotificationsRead,
      }}
    >
      {children}
    </RealtimeContext.Provider>
  );
};

export function useRealtime() {
  return useContext(RealtimeContext);
}

export function useRealtimeSubscription(
  eventPrefixes: string[],
  onEvent: (evt: RealtimeEvent) => void,
) {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;
  const prefixesKey = eventPrefixes.join("|");

  useEffect(() => {
    const prefixes = prefixesKey ? prefixesKey.split("|") : [];
    const listener = (e: Event) => {
      const evt = (e as CustomEvent<RealtimeEvent>).detail;
      if (!evt || !evt.event_type) return;
      if (prefixes.length === 0 || prefixes.some((p) => evt.event_type.startsWith(p))) {
        handlerRef.current(evt);
      }
    };
    window.addEventListener("aegisstor:realtime-event", listener);
    return () => window.removeEventListener("aegisstor:realtime-event", listener);
  }, [prefixesKey]);
}

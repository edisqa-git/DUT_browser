export type CpuCore = {
  usr: number;
  sys: number;
  nic: number;
  idle: number;
  io: number;
  irq: number;
  sirq: number;
};

export type WifiClient = {
  mac?: string;
  ip?: string;
  rssi?: number;
  snr?: number;
  [key: string]: unknown;
};

export type DashboardEvent =
  | { type: "console_line"; text: string }
  | {
      type: "snapshot_update";
      snapshot: {
        test_count: number;
        device_ts: string;
        cpu: Record<string, CpuCore>;
        wifi_clients?: Record<string, { total_size: number; clients: WifiClient[] }>;
      };
    }
  | {
      type: "wifi_clients_update";
      radio: "2G" | "5G" | "6G";
      total_size: number;
      clients: WifiClient[];
    }
  | { type: string; [key: string]: unknown };

export function connectDashboardWebSocket(onEvent: (event: DashboardEvent) => void): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/ws`);

  ws.onmessage = (message: MessageEvent<string>) => {
    try {
      const event = JSON.parse(message.data) as DashboardEvent;
      if (event && typeof event === "object" && "type" in event) {
        onEvent(event);
      }
    } catch {
      // Ignore malformed messages.
    }
  };

  return ws;
}

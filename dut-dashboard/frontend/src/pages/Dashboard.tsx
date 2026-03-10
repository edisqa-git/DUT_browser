import { useCallback, useEffect, useMemo, useState } from "react";

import { closeSerial, listSerialPorts, openSerial, sendSerial, SerialPortInfo } from "../api/rest";
import { connectDashboardWebSocket, WifiClient } from "../api/websocket";
import ClientsPanel from "../components/ClientsPanel";
import ConsolePanel from "../components/ConsolePanel";
import CpuChart, { CpuPoint } from "../components/CpuChart";

type Radio = "2G" | "5G" | "6G";
const DEFAULT_SERIAL_PORT = "/dev/ttyUSB0";

function choosePreferredPort(ports: SerialPortInfo[]): string {
  if (ports.length === 0) {
    return "";
  }
  const macosCuPort = ports.find((portInfo) => portInfo.device.startsWith("/dev/cu."));
  return macosCuPort ? macosCuPort.device : ports[0].device;
}

export default function Dashboard() {
  const [lines, setLines] = useState<string[]>([]);
  const [cpuPoints, setCpuPoints] = useState<CpuPoint[]>([]);
  const [coreKeys, setCoreKeys] = useState<string[]>([]);
  const [clientsByRadio, setClientsByRadio] = useState<Record<Radio, WifiClient[]>>({
    "2G": [],
    "5G": [],
    "6G": [],
  });
  const [mode, setMode] = useState<"serial" | "replay">("serial");
  const [port, setPort] = useState(DEFAULT_SERIAL_PORT);
  const [baudrate, setBaudrate] = useState(115200);
  const [replayPath, setReplayPath] = useState("logs/sample.log");
  const [replayIntervalMs, setReplayIntervalMs] = useState(100);
  const [serialPorts, setSerialPorts] = useState<SerialPortInfo[]>([]);
  const [portsLoading, setPortsLoading] = useState(false);
  const [portsError, setPortsError] = useState("");

  useEffect(() => {
    const ws = connectDashboardWebSocket((event) => {
      if (event.type === "console_line" && typeof event.text === "string") {
        setLines((prev) => [...prev.slice(-999), event.text]);
      }

      if (event.type === "snapshot_update" && event.snapshot && typeof event.snapshot === "object") {
        const nextPoint: CpuPoint = { device_ts: event.snapshot.device_ts };
        const nextCoreKeys: string[] = [];

        Object.entries(event.snapshot.cpu).forEach(([coreId, metrics]) => {
          const key = `CPU${coreId}`;
          nextCoreKeys.push(key);
          nextPoint[key] = Number((100 - Number(metrics.idle)).toFixed(2));
        });

        setCpuPoints((prev) => [...prev.slice(-299), nextPoint]);
        setCoreKeys((prev) => {
          const merged = new Set([...prev, ...nextCoreKeys]);
          return Array.from(merged).sort();
        });
      }

      if (event.type === "wifi_clients_update") {
        setClientsByRadio((prev) => ({
          ...prev,
          [event.radio]: event.clients,
        }));
      }
    });
    return () => ws.close();
  }, []);

  async function handleOpen() {
    await openSerial({
      mode,
      port,
      baudrate,
      replay_path: mode === "replay" ? replayPath : undefined,
      replay_interval_ms: replayIntervalMs,
    });
  }

  async function handleClose() {
    await closeSerial();
  }

  async function handleSend(text: string) {
    await sendSerial(text);
  }

  const refreshSerialPorts = useCallback(async () => {
    setPortsLoading(true);
    setPortsError("");
    try {
      const ports = await listSerialPorts();
      setSerialPorts(ports);
      if (ports.length > 0) {
        const preferredPort = choosePreferredPort(ports);
        setPort((prev) => {
          if (ports.some((portInfo) => portInfo.device === prev)) {
            return prev;
          }
          if (prev && prev !== DEFAULT_SERIAL_PORT) {
            return prev;
          }
          return preferredPort;
        });
      }
    } catch (error) {
      setPortsError(error instanceof Error ? error.message : "Failed to list serial ports");
    } finally {
      setPortsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (mode === "serial") {
      void refreshSerialPorts();
    }
  }, [mode, refreshSerialPorts]);

  const controls = useMemo(
    () => (
      <div style={{ border: "1px solid #ddd", padding: 12, marginBottom: 12 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <button onClick={() => setMode("serial")} disabled={mode === "serial"}>
            Serial Mode
          </button>
          <button onClick={() => setMode("replay")} disabled={mode === "replay"}>
            Replay Mode
          </button>
        </div>

        {mode === "serial" ? (
          <div style={{ display: "grid", gap: 8 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <select value={port} onChange={(e) => setPort(e.target.value)} style={{ flex: 1 }}>
                <option value="">Select detected serial port</option>
                {serialPorts.map((serialPort) => (
                  <option key={serialPort.device} value={serialPort.device}>
                    {serialPort.description ? `${serialPort.device} (${serialPort.description})` : serialPort.device}
                  </option>
                ))}
              </select>
              <button type="button" onClick={() => void refreshSerialPorts()} disabled={portsLoading}>
                {portsLoading ? "Refreshing..." : "Refresh Ports"}
              </button>
            </div>
            <input
              value={port}
              onChange={(e) => setPort(e.target.value)}
              placeholder="Or type serial port manually"
            />
            <input
              type="number"
              value={baudrate}
              onChange={(e) => setBaudrate(Number(e.target.value || 0))}
              placeholder="Baudrate"
            />
            {portsError ? <div style={{ color: "#b00020", fontSize: 12 }}>{portsError}</div> : null}
          </div>
        ) : (
          <div style={{ display: "flex", gap: 8 }}>
            <input value={replayPath} onChange={(e) => setReplayPath(e.target.value)} placeholder="Replay file" />
            <input
              type="number"
              value={replayIntervalMs}
              onChange={(e) => setReplayIntervalMs(Number(e.target.value || 0))}
              placeholder="Replay interval ms"
            />
          </div>
        )}

        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button onClick={handleOpen}>Open</button>
          <button onClick={handleClose}>Close</button>
        </div>
      </div>
    ),
    [mode, port, baudrate, replayPath, replayIntervalMs, serialPorts, portsLoading, portsError, refreshSerialPorts],
  );

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      <h1>DUT Dashboard - Milestone 3</h1>
      {controls}
      <CpuChart data={cpuPoints} coreKeys={coreKeys} />
      <ClientsPanel clientsByRadio={clientsByRadio} />
      <ConsolePanel lines={lines} onSend={handleSend} />
    </div>
  );
}

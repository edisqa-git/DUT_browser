import { useCallback, useEffect, useMemo, useState } from "react";

import {
  closeSerial,
  getSerialLogDownloadUrl,
  listSerialPorts,
  openSerial,
  sendSerial,
  SerialPortInfo,
} from "../api/rest";
import { connectDashboardWebSocket } from "../api/websocket";
import ConsolePanel from "../components/ConsolePanel";
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
  const [mode, setMode] = useState<"serial" | "replay">("serial");
  const [port, setPort] = useState(DEFAULT_SERIAL_PORT);
  const [baudrate, setBaudrate] = useState(115200);
  const [replayPath, setReplayPath] = useState("logs/sample.log");
  const [replayIntervalMs, setReplayIntervalMs] = useState(100);
  const [serialPorts, setSerialPorts] = useState<SerialPortInfo[]>([]);
  const [portsLoading, setPortsLoading] = useState(false);
  const [portsError, setPortsError] = useState("");
  const [currentLogFileName, setCurrentLogFileName] = useState("");

  useEffect(() => {
    const ws = connectDashboardWebSocket((event) => {
      if (event.type === "console_line" && typeof event.text === "string") {
        setLines((prev) => [...prev.slice(-999), event.text]);
      }
    });
    return () => ws.close();
  }, []);

  async function handleOpen() {
    const response = await openSerial({
      mode,
      port,
      baudrate,
      replay_path: mode === "replay" ? replayPath : undefined,
      replay_interval_ms: replayIntervalMs,
    });
    const logPath = response.log_path || "";
    const fileName = logPath.split(/[\\/]/).pop() || "";
    setCurrentLogFileName(fileName);
  }

  async function handleClose() {
    await closeSerial();
  }

  async function handleSend(text: string) {
    await sendSerial(text);
  }

  function handleDownloadLog() {
    if (!currentLogFileName) {
      return;
    }
    window.open(getSerialLogDownloadUrl(currentLogFileName), "_blank");
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
      <div style={{ border: "1px solid #ddd", padding: 12, marginBottom: 12, position: "relative" }}>
        <button
          onClick={handleClose}
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            width: 28,
            height: 28,
            background: "#d32f2f",
            color: "#fff",
            border: "1px solid #b71c1c",
            borderRadius: 6,
            fontSize: 16,
            fontWeight: 700,
            lineHeight: 1,
            cursor: "pointer",
          }}
          aria-label="Close serial connection"
          title="Close"
        >
          X
        </button>
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
              <select value={port} onChange={(e) => setPort(e.target.value)} style={{ width: 240 }}>
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
              placeholder="Manual serial port override (optional, e.g. /dev/ttyUSB0)"
              style={{ width: 240 }}
            />
            <input
              type="number"
              value={baudrate}
              onChange={(e) => setBaudrate(Number(e.target.value || 0))}
              placeholder="Baudrate"
              style={{ width: 140 }}
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

        <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "center", alignItems: "center" }}>
          <button
            onClick={handleOpen}
            style={{
              background: "#1976d2",
              color: "#fff",
              border: "1px solid #1565c0",
              padding: "10px 23px",
              fontSize: 16,
              fontWeight: 600,
              borderRadius: 6,
            }}
          >
            Open
          </button>
        </div>
      </div>
    ),
    [
      mode,
      port,
      baudrate,
      replayPath,
      replayIntervalMs,
      serialPorts,
      portsLoading,
      portsError,
      refreshSerialPorts,
      currentLogFileName,
    ],
  );

  return (
    <div style={{ fontFamily: "sans-serif", maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      <h1 style={{ textAlign: "center" }}>DUT Dashboard - Milestone 3</h1>
      {controls}
      <ConsolePanel
        lines={lines}
        onSend={handleSend}
        onDownloadLog={handleDownloadLog}
        canDownloadLog={Boolean(currentLogFileName)}
      />
    </div>
  );
}

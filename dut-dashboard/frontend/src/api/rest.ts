export type OpenSerialParams = {
  port: string;
  baudrate: number;
  mode?: "serial" | "replay";
  replay_path?: string;
  replay_interval_ms?: number;
};

export type SerialPortInfo = {
  device: string;
  description: string;
  hwid: string;
};

async function post<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as T;
}

async function get<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as T;
}

export async function openSerial(params: OpenSerialParams): Promise<{ ok: boolean }> {
  return post<{ ok: boolean }>("/api/serial/open", params);
}

export async function closeSerial(): Promise<{ ok: boolean }> {
  return post<{ ok: boolean }>("/api/serial/close", {});
}

export async function sendSerial(text: string): Promise<{ ok: boolean }> {
  return post<{ ok: boolean }>("/api/serial/send", { text });
}

export async function listSerialPorts(): Promise<SerialPortInfo[]> {
  const result = await get<{ ports: SerialPortInfo[] }>("/api/serial/ports");
  return result.ports;
}

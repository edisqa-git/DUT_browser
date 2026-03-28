import { apiUrl } from "./runtime";

export type OpenSerialParams = {
  port: string;
  baudrate: number;
  mode?: "serial" | "replay";
  replay_path?: string;
  replay_interval_ms?: number;
};

export type OpenSerialResponse = {
  ok: boolean;
  mode: "serial" | "replay";
  log_path?: string | null;
};

export type SerialPortInfo = {
  device: string;
  description: string;
  hwid: string;
};

export type HealthResponse = {
  ok: boolean;
  phase: string;
  version: string;
};

export type AppMeta = {
  product_name: string;
  current_version: string;
  repository: string;
  releases_page: string;
};

export type UpdateCheckResponse = {
  ok: boolean;
  current_version: string;
  latest_version: string;
  update_available: boolean;
  message: string;
  source: string;
  repository: string;
  checked_at: string;
  releases_page: string;
};

async function post<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(apiUrl(url), {
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
  const response = await fetch(apiUrl(url));
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as T;
}

export async function openSerial(params: OpenSerialParams): Promise<OpenSerialResponse> {
  return post<OpenSerialResponse>("/api/serial/open", params);
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

export async function getHealth(): Promise<HealthResponse> {
  return get<HealthResponse>("/health");
}

export async function getAppMeta(): Promise<AppMeta> {
  return get<AppMeta>("/api/app/meta");
}

export async function getUpdateCheck(force = false): Promise<UpdateCheckResponse> {
  const suffix = force ? "?force=true" : "";
  return get<UpdateCheckResponse>(`/api/app/update-check${suffix}`);
}

export function getSerialLogDownloadUrl(fileName: string): string {
  return apiUrl(`/api/serial/logs/${encodeURIComponent(fileName)}`);
}

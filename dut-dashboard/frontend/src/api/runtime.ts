declare global {
  interface Window {
    __TAURI__?: unknown;
  }
}

function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && Boolean(window.__TAURI__);
}

export function getApiBaseUrl(): string {
  const override = import.meta.env.VITE_API_BASE_URL;
  if (override) {
    return override;
  }
  if (import.meta.env.DEV) {
    return "";
  }
  if (isTauriRuntime()) {
    return "http://127.0.0.1:8765";
  }
  return "";
}

export function apiUrl(path: string): string {
  const base = getApiBaseUrl();
  return `${base}${path}`;
}

export function websocketUrl(path: string): string {
  const base = getApiBaseUrl();
  if (!base) {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    return `${protocol}://${window.location.host}${path}`;
  }
  const normalized = base.replace(/^http/i, "ws");
  return `${normalized}${path}`;
}

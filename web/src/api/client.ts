import type { CalcState, HealthResponse, Job, Snapshot } from "./types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(payload?.detail ?? `请求失败 (${response.status})`);
  }
  return (await response.json()) as T;
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function fetchCurrentSnapshot(): Promise<Snapshot> {
  return request<Snapshot>("/jobs/current");
}

export function startDemoJob(): Promise<Job> {
  return request<Job>("/jobs/start", { method: "POST" });
}

export function cancelCurrentJob(): Promise<Job> {
  return request<Job>("/jobs/cancel", { method: "POST" });
}

export function fetchCalcState(): Promise<CalcState> {
  return request<CalcState>("/calc/state");
}

export function pressCalcKey(key: string): Promise<CalcState> {
  return request<CalcState>("/calc/press", {
    method: "POST",
    body: JSON.stringify({ key }),
  });
}

export function eventsWebSocketUrl(): string {
  const configuredUrl = import.meta.env.VITE_WS_URL as string | undefined;
  if (configuredUrl) {
    return configuredUrl;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${apiBaseUrl}/events`;
}
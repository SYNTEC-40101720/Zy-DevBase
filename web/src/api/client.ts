import type {
  HealthResponse,
  JobResponse,
  RuntimeSnapshot,
  ToolDescriptor,
  ToolListResponse,
  UpdateCheckResponse,
  UpdateProgressResponse,
} from "./types";

const API_PREFIX = "/api/v1";

declare global {
  interface Window {
    __DEVBASE_TOKEN__?: string;
    __DEVBASE_API_BASE__?: string;
  }
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function initialToken(): string {
  const injected = typeof window !== "undefined" ? window.__DEVBASE_TOKEN__ : undefined;
  const queryToken = typeof window !== "undefined"
    ? new URLSearchParams(window.location.search).get("token")
    : null;
  const stored = typeof sessionStorage !== "undefined"
    ? sessionStorage.getItem("devbase.localToken")
    : null;
  return injected || queryToken || stored || import.meta.env.VITE_LOCAL_TOKEN || "";
}

function initialBaseUrl(): string {
  if (typeof window !== "undefined" && window.__DEVBASE_API_BASE__) {
    return window.__DEVBASE_API_BASE__.replace(/\/$/, "");
  }
  return "";
}

export class ApiClient {
  private token: string;
  readonly baseUrl: string;

  constructor(baseUrl = initialBaseUrl(), token = initialToken()) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.token = token;
  }

  get hasToken(): boolean {
    return this.token.length > 0;
  }

  setToken(token: string): void {
    this.token = token;
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem("devbase.localToken", token);
    }
  }

  getToken(): string {
    return this.token;
  }

  async health(signal?: AbortSignal): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health", { signal });
  }

  async listTools(signal?: AbortSignal): Promise<ToolDescriptor[]> {
    const response = await this.request<ToolListResponse>("/tools", { signal });
    return response.tools;
  }

  async currentJob(signal?: AbortSignal): Promise<RuntimeSnapshot> {
    return this.request<RuntimeSnapshot>("/jobs/current", { signal });
  }

  async startJob(kind = "demo_long_task", input: Record<string, unknown> = {}): Promise<JobResponse> {
    return this.request<JobResponse>("/jobs/start", {
      method: "POST",
      body: JSON.stringify({ kind, input }),
    });
  }

  async cancelJob(): Promise<JobResponse> {
    return this.request<JobResponse>("/jobs/cancel", { method: "POST" });
  }

  async checkUpdate(signal?: AbortSignal): Promise<UpdateCheckResponse> {
    return this.request<UpdateCheckResponse>("/updates/check", { signal });
  }

  async applyUpdate(): Promise<UpdateProgressResponse> {
    return this.request<UpdateProgressResponse>("/updates/apply", { method: "POST" });
  }

  async updateProgress(signal?: AbortSignal): Promise<UpdateProgressResponse> {
    return this.request<UpdateProgressResponse>("/updates/progress", { signal });
  }

  websocketUrl(after = 0): string {
    const base = this.baseUrl || window.location.origin;
    const url = new URL(`${base}${API_PREFIX}/events`);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.searchParams.set("after", String(Math.max(0, after)));
    if (this.token) url.searchParams.set("token", this.token);
    return url.toString();
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body) headers.set("Content-Type", "application/json");
    if (this.token) headers.set("X-Local-Token", this.token);

    const response = await fetch(`${this.baseUrl}${API_PREFIX}${path}`, {
      ...init,
      headers,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof payload.detail === "string"
        ? payload.detail
        : `API request failed: ${response.status}`;
      throw new ApiError(response.status, detail);
    }
    return payload as T;
  }
}

export const apiClient = new ApiClient();

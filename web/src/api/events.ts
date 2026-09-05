import type { ConnectionStatus, RuntimeEvent, RuntimeSnapshot } from "./types";
import type { ApiClient } from "./client";

export interface RuntimeEventStreamOptions {
  onStatus?: (status: ConnectionStatus) => void;
  onSnapshot?: (snapshot: RuntimeSnapshot) => void;
  onEvent?: (event: RuntimeEvent) => void;
  reconnect?: boolean;
  reconnectDelayMs?: number;
}

export class RuntimeEventStream {
  private socket: WebSocket | null = null;
  private reconnectTimer: number | undefined;
  private reconnectAttempt = 0;
  private cursor = 0;
  private closed = false;

  constructor(
    private readonly client: ApiClient,
    private readonly options: RuntimeEventStreamOptions = {},
  ) {}

  connect(after = this.cursor): void {
    this.closed = false;
    this.cursor = Math.max(this.cursor, after);
    this.open();
  }

  close(): void {
    this.closed = true;
    if (this.reconnectTimer !== undefined) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }
    this.socket?.close();
    this.socket = null;
    this.options.onStatus?.("idle");
  }

  get eventCursor(): number {
    return this.cursor;
  }

  private open(): void {
    if (this.closed) return;
    this.options.onStatus?.("connecting");
    const socket = new WebSocket(this.client.websocketUrl(this.cursor));
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectAttempt = 0;
      this.options.onStatus?.("connected");
    };
    socket.onmessage = (message) => this.handleMessage(message.data);
    socket.onerror = () => {
      if (this.client.hasToken) this.options.onStatus?.("disconnected");
    };
    socket.onclose = (event) => {
      this.socket = null;
      if (event.code === 1008) {
        this.options.onStatus?.("unauthorized");
      } else {
        this.options.onStatus?.("disconnected");
      }
      this.scheduleReconnect();
    };
  }

  private handleMessage(raw: string): void {
    let message: {
      type: "health" | "snapshot" | "event";
      data: RuntimeSnapshot | RuntimeEvent;
    };
    try {
      message = JSON.parse(raw) as typeof message;
    } catch {
      return;
    }
    if (message.type === "snapshot") {
      const snapshot = message.data as RuntimeSnapshot;
      this.cursor = snapshot.event_cursor;
      this.options.onSnapshot?.(snapshot);
      return;
    }
    if (message.type === "event") {
      const event = message.data as RuntimeEvent;
      this.cursor = Math.max(this.cursor, event.sequence);
      this.options.onEvent?.(event);
    }
  }

  private scheduleReconnect(): void {
    if (this.closed || this.options.reconnect === false) return;
    const base = this.options.reconnectDelayMs ?? 500;
    const delay = Math.min(5000, base * 2 ** this.reconnectAttempt);
    this.reconnectAttempt += 1;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = undefined;
      this.open();
    }, delay);
  }
}

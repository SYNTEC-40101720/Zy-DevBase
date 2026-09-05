import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { RuntimeEventStream } from "./events";
import type { ApiClient } from "./client";

// ---------------------------------------------------------------------------
// Minimal fake WebSocket + ApiClient for testing the reconnect-with-cursor
// logic described in Issue #8.
// ---------------------------------------------------------------------------

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  url: string;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  send(_: string) {}

  fireOpen() {
    this.onopen?.();
  }

  fireMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  fireClose(code = 1006) {
    this.onclose?.({ code });
  }
}

function makeClient(): ApiClient {
  return {
    baseUrl: "",
    hasToken: true,
    websocketUrl: vi.fn((after = 0) => `ws://test/events?after=${after}&token=t`),
  } as unknown as ApiClient;
}

describe("RuntimeEventStream — cursor reconnect", () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    (globalThis as unknown as { WebSocket: typeof FakeWebSocket }).WebSocket =
      FakeWebSocket;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("reconnects with the last cursor after a drop", async () => {
    vi.useFakeTimers();
    const client = makeClient();
    const stream = new RuntimeEventStream(client, { reconnectDelayMs: 100 });

    stream.connect(0);
    const ws1 = FakeWebSocket.instances[0];
    ws1.fireOpen();
    expect(client.websocketUrl).toHaveBeenLastCalledWith(0);

    // Receive a job_succeeded event at sequence 5
    ws1.fireMessage({
      type: "snapshot",
      data: { job: null, events: [], event_cursor: 5 },
    });
    expect(stream.eventCursor).toBe(5);

    // Receive an event at sequence 6
    ws1.fireMessage({
      type: "event",
      data: {
        sequence: 6,
        event_id: "e6",
        job_id: "j1",
        kind: "job_succeeded",
        status: "succeeded",
        progress: 100,
        message: "done",
        created_at: "2025-01-01T00:00:00Z",
      },
    });
    expect(stream.eventCursor).toBe(6);

    // Drop connection; reconnect is scheduled
    const statusSpy = vi.fn();
    stream.options.onStatus = statusSpy;
    ws1.fireClose(1006);
    expect(statusSpy).toHaveBeenCalledWith("disconnected");

    // Advance timers to trigger reconnect
    await vi.advanceTimersByTimeAsync(100);

    const ws2 = FakeWebSocket.instances[1];
    expect(ws2).toBeDefined();
    // The reconnect URL must carry the last cursor
    expect(client.websocketUrl).toHaveBeenLastCalledWith(6);
    expect(ws2.url).toContain("after=6");

    stream.close();
  });

  it("does not reconnect when reconnect is false", async () => {
    vi.useFakeTimers();
    const client = makeClient();
    const stream = new RuntimeEventStream(client, { reconnect: false });

    stream.connect();
    const ws = FakeWebSocket.instances[0];
    ws.fireOpen();
    ws.fireClose(1006);

    await vi.advanceTimersByTimeAsync(5000);

    expect(FakeWebSocket.instances).toHaveLength(1);
    stream.close();
  });

  it("updates cursor from snapshot on reconnect", async () => {
    vi.useFakeTimers();
    const client = makeClient();
    const stream = new RuntimeEventStream(client, {
      reconnectDelayMs: 100,
    });

    stream.connect(0);
    const ws1 = FakeWebSocket.instances[0];
    ws1.fireOpen();

    // Cursor updated to 10 from snapshot
    ws1.fireMessage({
      type: "snapshot",
      data: { job: null, events: [], event_cursor: 10 },
    });
    ws1.fireClose(1006);

    // Reconnect should use cursor=10
    await vi.advanceTimersByTimeAsync(100);
    const ws2 = FakeWebSocket.instances[1];
    expect(ws2.url).toContain("after=10");

    // New snapshot updates cursor to 15
    ws2.fireOpen();
    ws2.fireMessage({
      type: "snapshot",
      data: { job: null, events: [], event_cursor: 15 },
    });
    expect(stream.eventCursor).toBe(15);

    stream.close();
  });
});

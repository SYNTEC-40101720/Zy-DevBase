import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  Check,
  CircleAlert,
  CircleDot,
  Loader,
  Play,
  Square,
} from "lucide-react";

import {
  cancelCurrentJob,
  eventsWebSocketUrl,
  fetchCurrentSnapshot,
  fetchHealth,
  startDemoJob,
} from "../api/client";
import type {
  EventKind,
  HealthResponse,
  Job,
  JobStatus,
  RuntimeEvent,
  Snapshot,
  SocketMessage,
} from "../api/types";

/* ============================================================
 *  运行控制台（任务流视图）
 *  - 底部输入框提交指令
 *  - 消息流：用户消息 + 助手执行流（实时事件追加）
 *  - 执行中输入框变为"停止"按钮
 *  - 单任务约束：执行中不可再提交
 * ============================================================ */

type ChatRole = "user" | "assistant";

interface ChatSegment {
  kind: EventKind | "text" | "pending";
  text: string;
  progress?: number;
  sequence?: number;
  event_id?: string;
  time: string;
}

interface ChatMessage {
  id: string;
  role: ChatRole;
  text: string;
  segments: ChatSegment[];
  job_id?: string;
  status?: JobStatus;
}

type SocketState = "connecting" | "connected" | "disconnected";

const EMPTY_SNAPSHOT: Snapshot = { job: null, events: [], event_cursor: 0 };

const STATUS_LABELS: Record<JobStatus, string> = {
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  cancelled: "已取消",
  failed: "失败",
};

function isActive(job: Job | null): boolean {
  return job !== null && !["completed", "cancelled", "failed"].includes(job.status);
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

function appendEventToAssistant(
  msg: ChatMessage,
  event: RuntimeEvent,
): ChatMessage {
  if (msg.segments.some((s) => s.sequence === event.sequence)) return msg;
  const segment: ChatSegment = {
    kind: event.kind,
    text: event.message,
    progress: event.progress,
    sequence: event.sequence,
    event_id: event.event_id,
    time: formatTime(event.created_at),
  };
  let segments = msg.segments;
  if (
    event.kind === "progress" &&
    segments.length > 0 &&
    segments[segments.length - 1].kind === "progress"
  ) {
    segments = [...segments.slice(0, -1), segment];
  } else {
    segments = [...segments, segment];
  }
  segments = segments.filter((s) => s.kind !== "pending");
  return { ...msg, segments, status: event.status };
}

function socketMessage(value: string): SocketMessage | null {
  try {
    return JSON.parse(value) as SocketMessage;
  } catch {
    return null;
  }
}

function eventIcon(seg: ChatSegment) {
  switch (seg.kind) {
    case "job_completed":
      return <Check size={13} />;
    case "job_cancelled":
      return <Square size={11} />;
    case "job_failed":
      return <CircleAlert size={12} />;
    case "job_started":
      return <Play size={10} fill="currentColor" />;
    case "progress":
      return <CircleDot size={10} />;
    default:
      return <CircleDot size={10} />;
  }
}

function mergeEvent(snapshot: Snapshot, event: RuntimeEvent): Snapshot {
  const events = [
    ...snapshot.events.filter(
      (item) =>
        item.sequence !== event.sequence &&
        !(item.kind === "progress" &&
          event.kind === "progress" &&
          item.job_id === event.job_id),
    ),
    event,
  ].sort((l, r) => l.sequence - r.sequence);
  const job =
    snapshot.job?.id === event.job_id
      ? {
          ...snapshot.job,
          status: event.status,
          progress: event.progress,
          message: event.message,
          updated_at: event.created_at,
        }
      : snapshot.job;
  return {
    job,
    events,
    event_cursor: Math.max(snapshot.event_cursor, event.sequence),
  };
}

interface ConsoleProps {
  onToggleNav: () => void;
}

export default function Console({ onToggleNav }: ConsoleProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot>(EMPTY_SNAPSHOT);
  const [socketState, setSocketState] = useState<SocketState>("connecting");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const activeAssistantRef = useRef<string | null>(null);

  useEffect(() => {
    let disposed = false;
    let reconnectTimer: number | undefined;
    let reconnectDelay = 1000;

    const loadSnapshot = async () => {
      try {
        const next = await fetchCurrentSnapshot();
        if (!disposed) setSnapshot(next);
      } catch { /* 静默 */ }
    };
    const loadHealth = async () => {
      try {
        const next = await fetchHealth();
        if (!disposed) setHealth(next);
      } catch { /* 静默 */ }
    };

    const connect = () => {
      if (disposed) return;
      setSocketState("connecting");
      const socket = new WebSocket(eventsWebSocketUrl());
      socketRef.current = socket;
      socket.onopen = () => {
        reconnectDelay = 1000;
        setSocketState("connected");
        void loadSnapshot();
      };
      socket.onmessage = (message) => {
        const next = socketMessage(message.data);
        if (!next) return;
        if (next.type === "health") {
          setHealth(next.data);
        } else if (next.type === "snapshot") {
          setSnapshot(next.data);
        } else {
          setSnapshot((cur) => mergeEvent(cur, next.data));
          routeEvent(next.data);
        }
      };
      socket.onerror = () => socket.close();
      socket.onclose = () => {
        if (disposed) return;
        setSocketState("disconnected");
        reconnectTimer = window.setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 8000);
      };
    };

    void loadHealth();
    void loadSnapshot();
    connect();

    return () => {
      disposed = true;
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  const routeEvent = (event: RuntimeEvent) => {
    setMessages((prev) => {
      const assistantId = activeAssistantRef.current;
      if (!assistantId) return prev;
      const idx = prev.findIndex((m) => m.id === assistantId);
      if (idx < 0) return prev;
      const updated = appendEventToAssistant(prev[idx], event);
      const next = [...prev];
      next[idx] = updated;
      return next;
    });
  };

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const job = snapshot.job;
  const active = isActive(job);
  const socketConnected = socketState === "connected";

  const submit = async () => {
    const text = input.trim();
    if (!text || submitting) return;

    setSubmitting(true);
    setError(null);

    const userMsg: ChatMessage = { id: uid(), role: "user", text, segments: [] };
    const assistantId = uid();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      text: "",
      segments: [{ kind: "pending", text: "正在执行…", time: "" }],
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    activeAssistantRef.current = assistantId;
    setInput("");

    try {
      await startDemoJob();
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                segments: [
                  {
                    kind: "text",
                    text: err instanceof Error ? err.message : "提交失败",
                    time: formatTime(new Date().toISOString()),
                  },
                ],
                status: "failed",
              }
            : m,
        ),
      );
      setError(err instanceof Error ? err.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const stop = async () => {
    setError(null);
    try {
      await cancelCurrentJob();
    } catch (err) {
      setError(err instanceof Error ? err.message : "停止失败");
    }
  };

  useEffect(() => {
    if (!job) {
      activeAssistantRef.current = null;
      return;
    }
    if (job.status === "completed" || job.status === "failed" || job.status === "cancelled") {
      const aid = activeAssistantRef.current;
      if (aid) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aid
              ? {
                  ...m,
                  status: job.status,
                  segments: m.segments.map((s) =>
                    s.kind === "pending"
                      ? { ...s, kind: "text", text: STATUS_LABELS[job.status] }
                      : s,
                  ),
                }
              : m,
          ),
        );
        activeAssistantRef.current = null;
      }
    }
  }, [job?.status]);

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  };

  const newChat = () => {
    setMessages([]);
    activeAssistantRef.current = null;
    setError(null);
    inputRef.current?.focus();
  };

  return (
    <div className="workbench">
      <header className="topbar">
        <button
          type="button"
          className="calc-hamburger"
          aria-label="切换侧边栏"
          title="切换侧边栏"
          onClick={onToggleNav}
        >
          <span className="calc-hamburger-lines" aria-hidden="true" />
        </button>
        <div className="topbar-title">
          <span className="section-kicker">PLATFORM RUNTIME</span>
          <h1>运行控制台</h1>
        </div>
        <div className="connection-status">
          {socketConnected ? <></> : <></>}
          <span>{socketConnected ? "实时连接" : socketState === "connecting" ? "连接中" : "等待重连"}</span>
          <span className={`connection-dot ${socketConnected ? "is-online" : ""}`} />
        </div>
      </header>

      <div className="health-strip">
        <span className={`health-mark ${health?.status === "ok" ? "is-healthy" : ""}`}>
          {health?.status === "ok" ? <Check size={12} strokeWidth={2.5} /> : <CircleDot size={12} />}
        </span>
        <span className="health-label">
          {health?.status === "ok" ? "后端就绪" : "等待后端"}
        </span>
        <span className="health-meta">{health?.service ?? "—"}</span>
        <span className="health-divider" />
        <span className="health-meta">
          事件 {snapshot.events.length} · 游标 {snapshot.event_cursor}
        </span>
      </div>

      <main className="chat-scroll" ref={scrollRef}>
        <div className="chat-inner">
          {messages.length === 0 ? (
            <div className="chat-empty">
              <div className="chat-empty-icon">
                <CircleDot size={28} strokeWidth={1.4} />
              </div>
              <h2>运行控制台已就绪</h2>
              <p>在下方输入框提交指令，任务进度会实时流式显示在这里。</p>
              <p className="chat-empty-hint">按 Enter 提交 · Shift+Enter 换行</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`chat-msg chat-${msg.role}`}>
                <div className="chat-avatar">{msg.role === "user" ? "你" : "P"}</div>
                <div className="chat-body">
                  {msg.text && <p className="chat-text">{msg.text}</p>}
                  {msg.role === "assistant" && msg.segments.length > 0 && (
                    <div className="chat-segments">
                      {msg.segments.map((seg, i) => (
                        <div key={seg.event_id ?? i} className={`segment segment-${seg.kind}`}>
                          <span className="segment-icon">
                            {seg.kind === "pending" ? <Loader size={12} className="spin" /> : eventIcon(seg)}
                          </span>
                          <span className="segment-text">{seg.text}</span>
                          {seg.kind === "progress" && seg.progress !== undefined && (
                            <span className="segment-progress">{seg.progress}%</span>
                          )}
                          {seg.time && <span className="segment-time">{seg.time}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                  {msg.role === "assistant" && msg.status && (
                    <div className={`chat-status chat-status-${msg.status}`}>
                      {STATUS_LABELS[msg.status]}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {error && (
            <div className="chat-error">
              <CircleAlert size={14} />
              <span>{error}</span>
            </div>
          )}
        </div>
      </main>

      <footer className="composer">
        <div className="composer-box">
          <textarea
            ref={inputRef}
            className="composer-input"
            placeholder={active ? "任务执行中… 点击右侧停止" : "输入指令，Enter 提交"}
            value={input}
            rows={1}
            disabled={active}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
          />
          {active ? (
            <button className="composer-stop" type="button" onClick={() => void stop()} title="停止当前任务">
              <Square size={15} fill="currentColor" />
              停止
            </button>
          ) : (
            <button
              className="composer-send"
              type="button"
              disabled={!input.trim() || submitting}
              onClick={() => void submit()}
              title="提交"
            >
              {submitting ? <Loader size={16} className="spin" /> : <ArrowUp size={17} />}
            </button>
          )}
        </div>
        <div className="composer-hint">
          <span>内存运行时 · 单任务约束 · WebSocket 事件流</span>
          <span>Enter 提交 · Shift+Enter 换行</span>
        </div>
      </footer>
    </div>
  );
}

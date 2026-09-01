import { useEffect, useRef, useState } from "react";
import {
  Activity,
  Ban,
  Check,
  CircleAlert,
  CircleDot,
  FileClock,
  Loader,
  Play,
  RotateCw,
  Square,
  Wifi,
  WifiOff,
  X,
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

const EMPTY_SNAPSHOT: Snapshot = {
  job: null,
  events: [],
  event_cursor: 0,
};

const STATUS_LABELS: Record<JobStatus, string> = {
  queued: "排队中",
  running: "运行中",
  completed: "已完成",
  cancelled: "已取消",
  failed: "失败",
};

const EVENT_LABELS: Record<EventKind, string> = {
  job_created: "任务创建",
  job_started: "开始执行",
  progress: "进度更新",
  job_completed: "任务完成",
  job_cancelled: "任务取消",
  job_failed: "任务失败",
};

const CLOSE_MODE_LABELS: Record<HealthResponse["window_close_mode"], string> = {
  stop_on_close: "关闭窗口时停止任务",
  continue_on_close: "关闭窗口后继续任务",
};

type SocketState = "connecting" | "connected" | "disconnected";

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
  ].sort((left, right) => left.sequence - right.sequence);
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

function socketMessage(value: string): SocketMessage | null {
  try {
    return JSON.parse(value) as SocketMessage;
  } catch {
    return null;
  }
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot>(EMPTY_SNAPSHOT);
  const [socketState, setSocketState] = useState<SocketState>("connecting");
  const [action, setAction] = useState<"start" | "cancel" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let disposed = false;
    let reconnectTimer: number | undefined;
    let reconnectDelay = 1000;

    const loadSnapshot = async () => {
      try {
        const nextSnapshot = await fetchCurrentSnapshot();
        if (!disposed) {
          setSnapshot(nextSnapshot);
        }
      } catch (loadError) {
        if (!disposed) {
          setError(loadError instanceof Error ? loadError.message : "无法读取当前任务");
        }
      }
    };

    const loadHealth = async () => {
      try {
        const nextHealth = await fetchHealth();
        if (!disposed) {
          setHealth(nextHealth);
        }
      } catch (loadError) {
        if (!disposed) {
          setError(loadError instanceof Error ? loadError.message : "无法连接后端");
        }
      }
    };

    const connect = () => {
      if (disposed) {
        return;
      }
      setSocketState("connecting");
      const socket = new WebSocket(eventsWebSocketUrl());
      socketRef.current = socket;
      socket.onopen = () => {
        reconnectDelay = 1000;
        setSocketState("connected");
        void loadSnapshot();
      };
      socket.onmessage = (message) => {
        const nextMessage = socketMessage(message.data);
        if (!nextMessage) {
          return;
        }
        if (nextMessage.type === "health") {
          setHealth(nextMessage.data);
        } else if (nextMessage.type === "snapshot") {
          setSnapshot(nextMessage.data);
        } else {
          setSnapshot((current) => mergeEvent(current, nextMessage.data));
        }
      };
      socket.onerror = () => socket.close();
      socket.onclose = () => {
        if (disposed) {
          return;
        }
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
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer);
      }
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  const runAction = async (kind: "start" | "cancel") => {
    setAction(kind);
    setError(null);
    try {
      const job = kind === "start" ? await startDemoJob() : await cancelCurrentJob();
      setSnapshot((current) => ({ ...current, job }));
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "操作失败");
    } finally {
      setAction(null);
    }
  };

  const job = snapshot.job;
  const active = isActive(job);
  const socketConnected = socketState === "connected";

  return (
    <div className="app-shell">
      <aside className="activity-rail" aria-label="工具栏">
        <div className="rail-mark">P</div>
        <nav className="rail-nav" aria-label="工作台视图">
          <button className="rail-button is-selected" type="button" title="运行概览" aria-label="运行概览">
            <Activity size={19} strokeWidth={1.8} />
          </button>
          <button className="rail-button" type="button" title="任务记录" aria-label="任务记录">
            <FileClock size={19} strokeWidth={1.8} />
          </button>
        </nav>
        <div className="rail-bottom">
          <button className="rail-button" type="button" title="刷新连接" aria-label="刷新连接" onClick={() => window.location.reload()}>
            <RotateCw size={18} strokeWidth={1.8} />
          </button>
        </div>
      </aside>

      <div className="workbench">
        <header className="topbar">
          <div className="topbar-title">
            <span className="section-kicker">PLATFORM RUNTIME / TEMPLATE</span>
            <h1>运行控制台</h1>
          </div>
          <div className="connection-status">
            {socketConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
            <span>{socketConnected ? "实时连接" : socketState === "connecting" ? "连接中" : "等待重连"}</span>
            <span className={`connection-dot ${socketConnected ? "is-online" : ""}`} />
          </div>
        </header>

        <main className="content">
          <section className="intro-band">
            <div>
              <span className="section-kicker">LOCAL TOOL RUNTIME</span>
              <h2>轻量任务，清晰可见。</h2>
              <p>内存运行时 · 单任务约束 · WebSocket 事件流</p>
            </div>
            <div className="intro-index" aria-label="模板版本">
              <span>RUNTIME</span>
              <strong>0.1</strong>
            </div>
          </section>

          <section className="workspace-grid">
            <div className="panel control-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">CONTROL</span>
                  <h3>任务控制</h3>
                </div>
                <CircleDot className="heading-icon" size={22} />
              </div>
              <div className="health-line">
                <span className={`health-mark ${health?.status === "ok" ? "is-healthy" : ""}`}>
                  <Check size={14} strokeWidth={2.5} />
                </span>
                <div>
                  <strong>{health?.status === "ok" ? "后端健康" : "等待健康检查"}</strong>
                  <span>{health?.service ?? "platform-runtime-template"}</span>
                </div>
              </div>
              <div className="action-row">
                <button
                  className="primary-button"
                  type="button"
                  disabled={active || action !== null}
                  onClick={() => void runAction("start")}
                >
                  <Play size={16} fill="currentColor" />
                  启动演示
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={!active || action !== null}
                  onClick={() => void runAction("cancel")}
                >
                  <Square size={15} fill="currentColor" />
                  取消任务
                </button>
              </div>
              {error && (
                <div className="error-line" role="alert">
                  <CircleAlert size={16} />
                  <span>{error}</span>
                </div>
              )}
              <div className="policy-line">
                <span>窗口关闭策略</span>
                <code>
                  {health?.window_close_mode ?? "unknown"}
                  {health?.window_close_mode
                    ? ` · ${CLOSE_MODE_LABELS[health.window_close_mode]}`
                    : ""}
                </code>
              </div>
            </div>

            <div className="panel job-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">CURRENT JOB</span>
                  <h3>{job ? job.kind : "暂无当前任务"}</h3>
                </div>
                <span className={`status-pill status-${job?.status ?? "idle"}`}>
                  {job ? STATUS_LABELS[job.status] : "空闲"}
                </span>
              </div>
              {job ? (
                <>
                  <div className="job-meta">
                    <span>ID</span>
                    <code>{job.id.slice(0, 8)}</code>
                    <span>更新于 {formatTime(job.updated_at)}</span>
                  </div>
                  <div className="progress-block">
                    <div className="progress-heading">
                      <span>执行进度</span>
                      <strong>{job.progress}%</strong>
                    </div>
                    <div className="progress-track" aria-label={`任务进度 ${job.progress}%`}>
                      <div className="progress-value" style={{ width: `${job.progress}%` }} />
                    </div>
                    <p>{job.message}</p>
                  </div>
                </>
              ) : (
                <div className="empty-job">
                  <Ban size={24} />
                  <span>启动后将在这里显示任务状态</span>
                </div>
              )}
            </div>
          </section>

          <section className="panel events-panel">
            <div className="panel-heading events-heading">
              <div>
                <span className="section-kicker">EVENT STREAM</span>
                <h3>事件与日志</h3>
              </div>
              <span className="event-count">{snapshot.events.length} 条 / 游标 {snapshot.event_cursor}</span>
            </div>
            <div className="event-list">
              {snapshot.events.length === 0 ? (
                <div className="empty-events">等待任务事件</div>
              ) : (
                snapshot.events.map((event) => (
                  <div className={`event-row ${event.kind === "progress" ? "is-progress" : "is-key"}`} key={event.event_id}>
                    <span className="event-sequence">{String(event.sequence).padStart(3, "0")}</span>
                    <span className="event-icon">
                      {event.kind === "job_completed"
                        ? <Check size={13} />
                        : event.kind === "job_cancelled"
                          ? <X size={12} />
                          : event.kind === "job_failed"
                            ? <CircleAlert size={12} />
                            : event.kind === "job_started"
                              ? <Play size={11} fill="currentColor" />
                              : <CircleDot size={11} />}
                    </span>
                    <span className="event-name">{EVENT_LABELS[event.kind]}</span>
                    <span className="event-message">{event.message}</span>
                    <span className="event-progress">{event.progress}%</span>
                    <time>{formatTime(event.created_at)}</time>
                  </div>
                ))
              )}
            </div>
          </section>
        </main>

        <footer className="statusbar">
          <span><span className={`statusbar-dot ${socketConnected ? "is-online" : ""}`} /> {socketConnected ? "事件流已连接" : "事件流未连接"}</span>
          <span>内存状态 · 无外部服务</span>
        </footer>
      </div>
    </div>
  );
}
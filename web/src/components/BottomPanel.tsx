import { ChevronDown, TerminalSquare } from "lucide-react";

import type { ConnectionStatus, RuntimeEvent } from "../api/types";

interface BottomPanelProps {
  onClose: () => void;
  connection: ConnectionStatus;
  events: RuntimeEvent[];
}

const eventLabel: Record<string, string> = {
  job_created: "创建",
  job_started: "启动",
  progress: "进度",
  job_cancelling: "取消中",
  job_succeeded: "成功",
  job_completed_with_warnings: "含警告完成",
  job_cancelled: "已取消",
  job_failed: "失败",
};

export function BottomPanel({ onClose, connection, events }: BottomPanelProps) {
  return (
    <section className="bottom-panel" aria-label="运行日志">
      <header className="bottom-panel-header">
        <div className="bottom-panel-title">
          <TerminalSquare size={15} strokeWidth={1.6} />
          <span>运行日志</span>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="收起日志" title="收起日志">
          <ChevronDown size={16} strokeWidth={1.6} />
        </button>
      </header>
      <div className="bottom-panel-body">
        {events.length === 0 ? (
          <span className="bottom-panel-empty">连接状态：{connection}。暂无日志。</span>
        ) : (
          <ul className="event-list" role="log">
            {events.map((event) => (
              <li key={event.event_id} className={`event-item event-kind-${event.kind}`}>
                <span className="event-time">
                  {new Date(event.created_at).toLocaleTimeString("zh-CN")}
                </span>
                <span className="event-label">{eventLabel[event.kind] ?? event.kind}</span>
                {event.message && <span className="event-message">{event.message}</span>}
                <span className="event-progress">
                  {event.kind === "progress" ? `${Math.round(event.progress)}%` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

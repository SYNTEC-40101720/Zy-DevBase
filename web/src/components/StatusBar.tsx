import { CheckCircle2, CircleAlert, LoaderCircle, RefreshCw, Wifi, WifiOff } from "lucide-react";

import type { ConnectionStatus } from "../api/types";

interface StatusBarProps {
  connection: ConnectionStatus;
  version: string;
  onTogglePanel: () => void;
  onCheckUpdate: () => void;
  panelOpen: boolean;
}

const labels: Record<ConnectionStatus, string> = {
  idle: "未启动",
  connecting: "连接中",
  connected: "已连接",
  disconnected: "已断开",
  unauthorized: "需要令牌",
};

export function StatusBar({ connection, version, onTogglePanel, onCheckUpdate, panelOpen }: StatusBarProps) {
  const icon = connection === "connected"
    ? <CheckCircle2 size={14} strokeWidth={1.7} />
    : connection === "connecting"
      ? <LoaderCircle className="status-spin" size={14} strokeWidth={1.7} />
      : connection === "unauthorized"
        ? <CircleAlert size={14} strokeWidth={1.7} />
        : <WifiOff size={14} strokeWidth={1.7} />;

  return (
    <footer className="status-bar">
      <button
        type="button"
        className={`status-connection status-connection-${connection}`}
        onClick={onTogglePanel}
        aria-expanded={panelOpen}
        title="连接与日志"
      >
        {icon}
        <span>{labels[connection]}</span>
      </button>
      <span className="status-spacer" />
      <span className="status-runtime"><Wifi size={13} strokeWidth={1.6} /> 本地运行时</span>
      <button type="button" className="status-update-check" onClick={onCheckUpdate} title="检查更新" aria-label="检查更新">
        <RefreshCw size={13} strokeWidth={1.6} />
      </button>
      <span className="status-version">v{version}</span>
    </footer>
  );
}

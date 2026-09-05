import { ChevronDown, TerminalSquare } from "lucide-react";

interface BottomPanelProps {
  onClose: () => void;
  connection: string;
}

export function BottomPanel({ onClose, connection }: BottomPanelProps) {
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
        <span className="bottom-panel-empty">连接状态：{connection}。暂无日志。</span>
      </div>
    </section>
  );
}

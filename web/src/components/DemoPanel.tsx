import { useCallback, useEffect, useRef, useState } from "react";
import {
  Hand,
  Maximize2,
  MonitorSmartphone,
  MousePointerClick,
  PanelsTopLeft,
  Plus,
  Sidebar as SidebarIcon,
  Sparkles,
  Trash2,
} from "lucide-react";

interface DemoPanelProps {
  sidebarCollapsed: boolean;
  sidebarWidth: number;
}

interface Toast {
  id: number;
  text: string;
}

interface CardItem {
  id: number;
  hue: number;
}

/* ============================================================
 *  演示面板 — 工作台空态交互测试区
 *  - ResizeObserver 追踪容器尺寸
 *  - 侧边栏折叠 / 宽度联动
 *  - 响应式卡片网格：随容器宽度自动 1→2→3→4 列
 *  - 计数器 / Toast / 进度条 / 折叠卡
 * ============================================================ */

export function DemoPanel({ sidebarCollapsed, sidebarWidth }: DemoPanelProps) {
  // ---- 容器尺寸 ----
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (cr) setSize({ w: Math.round(cr.width), h: Math.round(cr.height) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ---- 响应式列数 ----
  const columns = size.w < 360 ? 1 : size.w < 560 ? 2 : size.w < 780 ? 3 : 4;

  // ---- 计数器 ----
  const [count, setCount] = useState(0);

  // ---- Toast ----
  const [toasts, setToasts] = useState<Toast[]>([]);
  const pushToast = useCallback((text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text }]);
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 2400);
  }, []);

  // ---- 进度条 ----
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          setRunning(false);
          pushToast("进度完成");
          return 100;
        }
        return p + 4;
      });
    }, 60);
    return () => clearInterval(timer);
  }, [running, pushToast]);

  // ---- 可折叠卡 ----
  const [cardOpen, setCardOpen] = useState(true);

  // ---- 响应式卡片网格 ----
  const [cards, setCards] = useState<CardItem[]>(() =>
    Array.from({ length: 6 }, (_, i) => ({ id: i, hue: (i * 47) % 360 })),
  );
  const nextId = useRef(6);
  const addCard = () => {
    const id = nextId.current++;
    setCards((c) => [...c, { id, hue: (id * 47) % 360 }]);
    pushToast(`已添加卡片 #${id}`);
  };
  const clearCards = () => {
    setCards([]);
    pushToast("已清空卡片");
  };

  return (
    <div className="demo-panel" ref={containerRef}>
      {/* ---- Toast 区 ---- */}
      <div className="demo-toast-area">
        {toasts.map((t) => (
          <div key={t.id} className="demo-toast">{t.text}</div>
        ))}
      </div>

      {/* ---- 尺寸 & 侧边栏信息条 ---- */}
      <section className="demo-info-bar">
        <div className="demo-info-item">
          <Maximize2 size={14} strokeWidth={1.6} />
          <span className="demo-info-value">{size.w}×{size.h}</span>
          <span className="demo-info-label">容器</span>
        </div>
        <div className="demo-info-item">
          <SidebarIcon size={14} strokeWidth={1.6} />
          <span className="demo-info-value">
            {sidebarCollapsed ? "折叠" : "展开"} · {sidebarWidth}px
          </span>
          <span className="demo-info-label">侧边栏</span>
        </div>
        <div className="demo-info-item">
          <PanelsTopLeft size={14} strokeWidth={1.6} />
          <span className="demo-info-value">{columns} 列</span>
          <span className="demo-info-label">网格</span>
        </div>
      </section>

      <div className="demo-scroll">
        {/* ---- 交互动作卡 ---- */}
        <section className={`demo-card${cardOpen ? " is-open" : ""}`}>
          <header className="demo-card-head" onClick={() => setCardOpen((v) => !v)}>
            <span className="demo-card-icon">
              <Hand size={16} strokeWidth={1.6} />
            </span>
            <span className="demo-card-title">交互动作测试</span>
            <span className="demo-card-collapse">{cardOpen ? "▾" : "▸"}</span>
          </header>
          {cardOpen && (
            <div className="demo-card-body">
              {/* 计数器 */}
              <div className="demo-field">
                <span className="demo-field-label">计数器</span>
                <div className="demo-counter">
                  <button className="demo-btn-sm" onClick={() => setCount((c) => c - 1)}>−</button>
                  <span className="demo-counter-value">{count}</span>
                  <button className="demo-btn-sm" onClick={() => setCount((c) => c + 1)}>+</button>
                  <button className="demo-btn-sm" onClick={() => { setCount(0); pushToast("计数器已重置"); }}>重置</button>
                </div>
              </div>
              {/* Toast */}
              <div className="demo-field">
                <span className="demo-field-label">通知</span>
                <button
                  className="demo-btn"
                  onClick={() => pushToast(`通知 #${toasts.length + 1}`)}
                >
                  <Sparkles size={14} strokeWidth={1.6} /> 弹出通知
                </button>
              </div>
              {/* 进度条 */}
              <div className="demo-field">
                <span className="demo-field-label">进度 {progress}%</span>
                <div className="demo-progress">
                  <div className="demo-progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <button className="demo-btn" onClick={() => { setProgress(0); setRunning(true); }}>
                  <MousePointerClick size={14} strokeWidth={1.6} /> 开始进度
                </button>
              </div>
            </div>
          )}
        </section>

        {/* ---- 响应式卡片网格 ---- */}
        <section className="demo-card is-open">
          <header className="demo-card-head">
            <span className="demo-card-icon">
              <MonitorSmartphone size={16} strokeWidth={1.6} />
            </span>
            <span className="demo-card-title">响应式网格</span>
            <span className="demo-card-count">{cards.length} 项</span>
          </header>
          <div className="demo-card-body">
            <div className="demo-card-actions">
              <button className="demo-btn" onClick={addCard}>
                <Plus size={14} strokeWidth={1.6} /> 添加
              </button>
              <button className="demo-btn demo-btn-ghost" onClick={clearCards}>
                <Trash2 size={14} strokeWidth={1.6} /> 清空
              </button>
            </div>
            {cards.length > 0 ? (
              <div
                className="demo-grid"
                style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
              >
                {cards.map((c) => (
                  <div
                    key={c.id}
                    className="demo-grid-item"
                    style={{ background: `hsl(${c.hue}, 65%, 95%)`, borderColor: `hsl(${c.hue}, 50%, 80%)` }}
                  >
                    <span className="demo-grid-dot" style={{ background: `hsl(${c.hue}, 60%, 55%)` }} />
                    <span className="demo-grid-text">#{c.id}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="demo-empty-hint">网格为空，点击"添加"测试响应式布局。</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

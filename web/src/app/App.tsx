import { useCallback, useEffect, useRef, useState } from "react";
import {
  Calculator as CalcIcon,
  PanelLeft,
  Radio,
  Settings,
  X,
} from "lucide-react";

import Calculator from "./Calculator";
import Console from "./Console";

/* ============================================================
 *  工作台外壳 — 借鉴 DeepSeek Harness 侧边栏设计
 *  - CSS-grid 三列布局，sidebar 列宽通过 gridTemplateColumns 过渡
 *  - 侧边栏两态：
 *      折叠 (rail)  = 56px 纯图标列
 *      展开 (wide)  = 可拖拽调宽，默认 264px（clamp 232–360）
 *  - 结构：品牌行 → 新建按钮 → 导航列表(flex:1) → 底部设置
 *  - 拖拽手柄：col-resize 8px 覆盖条
 * ============================================================ */

type ViewId = "calculator" | "console";

interface NavItem {
  id: ViewId;
  title: string;
  subtitle: string;
  glyph: "calc" | "console";
}

const NAV: NavItem[] = [
  { id: "calculator", title: "计算器",    subtitle: "标准",     glyph: "calc" },
  { id: "console",    title: "运行控制台", subtitle: "平台运行时", glyph: "console" },
];

const RAIL_WIDTH = 56;
const MIN_WIDE = 232;
const MAX_WIDE = 360;

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}

export default function App() {
  const [view, setView] = useState<ViewId>("calculator");
  const [collapsed, setCollapsed] = useState(false);
  const [wideWidth, setWideWidth] = useState(264);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // ---- 拖拽调宽 ----
  const draggingRef = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const onDragStart = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    draggingRef.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = collapsed ? wideWidth : wideWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [collapsed, wideWidth]);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!draggingRef.current) return;
      const dx = e.clientX - dragStartX.current;
      const next = clamp(dragStartWidth.current + dx, MIN_WIDE, MAX_WIDE);
      setWideWidth(next);
      // 拖到 rail 宽度以下自动折叠（但保持 wideWidth 以便展开恢复）
      if (next <= MIN_WIDE && dx < 0) {
        // 不自动折叠，让用户用按钮折叠
      }
    };
    const onUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, []);

  const toggleSidebar = () => setCollapsed((v) => !v);
  const sidebarWidth = collapsed ? RAIL_WIDTH : wideWidth;

  return (
    <div
      className="app-frame"
      style={{ gridTemplateColumns: sidebarWidth + "px minmax(0,1fr)" }}
      data-sidebar-collapsed={collapsed || undefined}
    >
      {/* ============ 侧边栏 ============ */}
      <nav
        className={"sidebar" + (collapsed ? " is-collapsed" : "")}
        aria-label="导航"
      >
        {/* ---- 品牌行 ---- */}
        <div className="sidebar-brand-row">
          {!collapsed && (
            <button
              type="button"
              className="sidebar-brand"
              title="Platform"
              onClick={() => setView("calculator")}
            >
              <span className="sidebar-brand-mark">P</span>
              <span className="sidebar-brand-name">Platform</span>
            </button>
          )}
          {collapsed && (
            <span className="sidebar-brand-mark" title="Platform">P</span>
          )}
          <button
            type="button"
            className="sidebar-toggle"
            aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
            title={collapsed ? "展开侧边栏" : "收起侧边栏"}
            onClick={toggleSidebar}
          >
            <PanelLeft size={collapsed ? 18 : 16} strokeWidth={1.6} />
          </button>
        </div>

        {/* ---- 导航列表 ---- */}
        <div className="sidebar-region" role="navigation">
          {!collapsed && <div className="sidebar-section-label">工具</div>}
          <ul className="sidebar-nav-list">
            {NAV.map((n) => {
              const selected = view === n.id;
              const Icon = n.glyph === "calc" ? CalcIcon : Radio;
              return (
                <li key={n.id}>
                  <button
                    type="button"
                    className={"sidebar-nav-item" + (selected ? " is-selected" : "")}
                    title={n.title}
                    aria-current={selected ? "page" : undefined}
                    onClick={() => setView(n.id)}
                  >
                    <span className="sidebar-nav-icon">
                      <Icon size={18} strokeWidth={1.6} />
                    </span>
                    {!collapsed && (
                      <span className="sidebar-nav-text">
                        <span className="sidebar-nav-title">{n.title}</span>
                        <span className="sidebar-nav-sub">{n.subtitle}</span>
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        {/* ---- 底部设置 ---- */}
        <div className="sidebar-foot">
          <button
            type="button"
            className={"sidebar-settings-btn" + (settingsOpen ? " is-active" : "")}
            title="设置"
            aria-label="设置"
            aria-haspopup="dialog"
            aria-expanded={settingsOpen}
            onClick={() => setSettingsOpen((v) => !v)}
          >
            <Settings size={collapsed ? 18 : 16} strokeWidth={1.6} />
            {!collapsed && <span className="sidebar-settings-label">设置</span>}
          </button>
        </div>
      </nav>

      {/* ---- 拖拽手柄 ---- */}
      {!collapsed && (
        <div
          className="sidebar-drag-handle"
          style={{ left: sidebarWidth - 4 }}
          onPointerDown={onDragStart}
          aria-hidden="true"
        />
      )}

      {/* ============ 主区 ============ */}
      <div className="sidebar-center-col">
        {view === "calculator" ? (
          <Calculator onToggleNav={toggleSidebar} />
        ) : (
          <Console onToggleNav={toggleSidebar} />
        )}
      </div>

      {/* ============ 设置浮层 ============ */}
      {settingsOpen && (
        <div className="settings-overlay" role="dialog" aria-modal="true" aria-label="设置">
          <button
            type="button"
            className="settings-mask"
            aria-label="关闭设置"
            onClick={() => setSettingsOpen(false)}
          />
          <div className="settings-panel">
            <div className="settings-header">
              <span className="settings-title">设置</span>
              <button
                type="button"
                className="settings-close"
                aria-label="关闭"
                onClick={() => setSettingsOpen(false)}
              >
                <X size={15} strokeWidth={1.6} />
              </button>
            </div>
            <div className="settings-body">
              <div className="settings-section">
                <div className="settings-section-title">常规</div>
                <div className="settings-row">
                  <span>侧边栏默认宽度</span>
                  <span className="settings-row-value">{wideWidth}px</span>
                </div>
                <div className="settings-row">
                  <span>默认视图</span>
                  <span className="settings-row-value">
                    {view === "calculator" ? "计算器" : "运行控制台"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

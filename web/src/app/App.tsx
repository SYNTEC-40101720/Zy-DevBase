import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, LayoutGrid, Monitor, Moon, PanelLeft, Settings, Sun } from "lucide-react";
import appLogo from "../assets/app-logo.svg";

/* ============================================================
 *  工作台外壳 — 借鉴 DeepSeek Harness 侧边栏设计
 *  - CSS-grid 两列布局，sidebar 列宽通过 gridTemplateColumns 过渡
 *  - 侧边栏两态：
 *      折叠 (rail)  = 56px 纯图标列
 *      展开 (wide)  = 可拖拽调宽，默认 264px（clamp 232–360）
 *  - 结构：品牌行 → 导航列表(flex:1) → 底部设置
 *  - 拖拽手柄：col-resize 8px 覆盖条
 *  - 设置为内联视图，点底部"设置"切到设置页，不弹窗
 * ============================================================ */

type View = "workbench" | "settings";
type ThemeMode = "system" | "light" | "dark";

const RAIL_WIDTH = 56;
const MIN_WIDE = 232;
const MAX_WIDE = 360;

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}

export default function App() {
  const [view, setView] = useState<View>("workbench");
  const [collapsed, setCollapsed] = useState(false);
  const [wideWidth, setWideWidth] = useState(264);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    return (localStorage.getItem("theme") as ThemeMode) || "system";
  });

  // ---- 主题应用 ----
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") {
      delete root.dataset.theme;
      localStorage.removeItem("theme");
    } else {
      root.dataset.theme = theme;
      localStorage.setItem("theme", theme);
    }
  }, [theme]);

  // ---- 拖拽调宽 ----
  const draggingRef = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const onDragStart = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    draggingRef.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = wideWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [wideWidth]);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!draggingRef.current) return;
      const dx = e.clientX - dragStartX.current;
      setWideWidth(clamp(dragStartWidth.current + dx, MIN_WIDE, MAX_WIDE));
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
              title="Zy"
              onClick={() => setView("workbench")}
            >
              <img className="sidebar-brand-mark" src={appLogo} alt="Zy" />
              <span className="sidebar-brand-name">Zy</span>
            </button>
          )}
          {collapsed && (
            <>
              <img className="sidebar-brand-mark" src={appLogo} alt="Zy" title="Zy" />
              <button
                type="button"
                className="sidebar-toggle sidebar-toggle-rail"
                aria-label="展开侧边栏"
                title="展开侧边栏"
                onClick={toggleSidebar}
              >
                <PanelLeft size={18} strokeWidth={1.6} />
              </button>
            </>
          )}
          {!collapsed && (
            <button
              type="button"
              className="sidebar-toggle"
              aria-label="收起侧边栏"
              title="收起侧边栏"
              onClick={toggleSidebar}
            >
              <PanelLeft size={16} strokeWidth={1.6} />
            </button>
          )}
        </div>

        {/* ---- 导航列表 ---- */}
        <div className="sidebar-region" role="navigation">
          <ul className="sidebar-nav-list">
            <li>
              <button
                type="button"
                className={"sidebar-nav-item" + (view === "workbench" ? " is-selected" : "")}
                title="工作台"
                aria-current={view === "workbench" ? "page" : undefined}
                onClick={() => setView("workbench")}
              >
                <span className="sidebar-nav-icon">
                  <LayoutGrid size={18} strokeWidth={1.6} />
                </span>
                {!collapsed && (
                  <span className="sidebar-nav-text">
                    <span className="sidebar-nav-title">工作台</span>
                    <span className="sidebar-nav-sub">起始页</span>
                  </span>
                )}
              </button>
            </li>
          </ul>
        </div>

        {/* ---- 底部设置 ---- */}
        <div className="sidebar-foot">
          <button
            type="button"
            className={"sidebar-settings-btn" + (view === "settings" ? " is-active" : "")}
            title="设置"
            aria-label="设置"
            aria-current={view === "settings" ? "page" : undefined}
            onClick={() => setView("settings")}
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
        {view === "workbench" ? (
          <div className="workbench workbench-empty">
            <div className="empty-hero">
              <div className="empty-hero-icon">
                <LayoutGrid size={28} strokeWidth={1.4} />
              </div>
              <h2>工作台已就绪</h2>
              <p>这是一个空白模板。在此添加你的工具视图与业务逻辑。</p>
            </div>
          </div>
        ) : (
          <div className="workbench settings-view">
            <header className="settings-view-header">
              <button
                type="button"
                className="settings-view-back"
                aria-label="返回工作台"
                title="返回工作台"
                onClick={() => setView("workbench")}
              >
                <ArrowLeft size={18} strokeWidth={1.6} />
              </button>
              <h2 className="settings-view-title">设置</h2>
            </header>
            <div className="settings-view-body">
              <div className="settings-scroll">
                {/* ---- 外观卡片 ---- */}
                <section className="settings-card">
                  <div className="settings-card-head">
                    <span className="settings-card-icon"><Sun size={16} strokeWidth={1.6} /></span>
                    <div className="settings-card-meta">
                      <span className="settings-card-title">外观</span>
                      <span className="settings-card-desc">主题与侧边栏布局</span>
                    </div>
                  </div>
                  <div className="settings-card-body">
                    <div className="settings-field">
                      <div className="settings-field-label">主题模式</div>
                      <div className="theme-segmented" role="radiogroup" aria-label="主题">
                        {([
                          { id: "system", label: "跟随系统", icon: <Monitor size={15} strokeWidth={1.6} /> },
                          { id: "light", label: "浅色", icon: <Sun size={15} strokeWidth={1.6} /> },
                          { id: "dark", label: "暗色", icon: <Moon size={15} strokeWidth={1.6} /> },
                        ] as const).map((opt) => (
                          <button
                            key={opt.id}
                            type="button"
                            className={"theme-option" + (theme === opt.id ? " is-selected" : "")}
                            role="radio"
                            aria-checked={theme === opt.id}
                            onClick={() => setTheme(opt.id)}
                          >
                            {opt.icon}
                            <span>{opt.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="settings-field">
                      <div className="settings-field-label">
                        <span>侧边栏宽度</span>
                        <span className="settings-field-value">{wideWidth}px</span>
                      </div>
                      <input
                        type="range"
                        className="settings-range"
                        min={MIN_WIDE}
                        max={MAX_WIDE}
                        step={1}
                        value={wideWidth}
                        onChange={(e) => setWideWidth(Number(e.target.value))}
                        aria-label="侧边栏宽度"
                      />
                      <div className="settings-range-ticks">
                        <span>窄</span>
                        <span>宽</span>
                      </div>
                    </div>
                  </div>
                </section>

                {/* ---- 关于卡片 ---- */}
                <section className="settings-card">
                  <div className="settings-card-head">
                    <span className="settings-card-icon"><LayoutGrid size={16} strokeWidth={1.6} /></span>
                    <div className="settings-card-meta">
                      <span className="settings-card-title">关于</span>
                      <span className="settings-card-desc">模板信息</span>
                    </div>
                  </div>
                  <div className="settings-card-body">
                    <dl className="settings-kv">
                      <div className="settings-kv-row">
                        <dt>名称</dt>
                        <dd>Zy</dd>
                      </div>
                      <div className="settings-kv-row">
                        <dt>版本</dt>
                        <dd>0.1.0</dd>
                      </div>
                      <div className="settings-kv-row">
                        <dt>技术栈</dt>
                        <dd>Python · FastAPI · React · Vite</dd>
                      </div>
                    </dl>
                  </div>
                </section>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

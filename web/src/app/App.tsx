import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, LayoutGrid, Monitor, Moon, Sun } from "lucide-react";

import { RuntimeEventStream } from "../api/events";
import { apiClient } from "../api/client";
import { BottomPanel } from "../components/BottomPanel";
import { Sidebar } from "../components/Sidebar";
import { StatusBar } from "../components/StatusBar";
import { UpdateBanner } from "../components/UpdateBanner";
import { useWorkbenchStore, workbenchStore } from "../store/workbench";

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
const APP_VERSION = import.meta.env.VITE_APP_VERSION || "0.1.0";

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}

export default function App() {
  const [view, setView] = useState<View>("workbench");
  const [collapsed, setCollapsed] = useState(false);
  const [wideWidth, setWideWidth] = useState(264);
  const { tools, selectedTool, connection, bottomPanelOpen, updateStatus } = useWorkbenchStore();
  const selectedToolDescriptor = tools.find((tool) => tool.kind === selectedTool);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    return (localStorage.getItem("theme") as ThemeMode) || "system";
  });

  useEffect(() => {
    if (!apiClient.hasToken) {
      workbenchStore.patch({ connection: "unauthorized" });
      return;
    }

    const controller = new AbortController();
    apiClient.listTools(controller.signal)
      .then((loadedTools) => workbenchStore.patch({ tools: loadedTools }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          workbenchStore.patch({ connection: error instanceof Error && "status" in error && error.status === 401 ? "unauthorized" : "disconnected" });
        }
      });

    const stream = new RuntimeEventStream(apiClient, {
      onStatus: (status) => workbenchStore.patch({ connection: status }),
      onSnapshot: () => undefined,
      onEvent: () => undefined,
    });
    stream.connect();
    return () => {
      controller.abort();
      stream.close();
    };
  }, []);

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
  const selectTool = (kind: string) => {
    workbenchStore.patch({ selectedTool: kind });
    setView("workbench");
  };
  const toggleBottomPanel = () => {
    workbenchStore.patch({ bottomPanelOpen: !bottomPanelOpen });
  };
  const checkForUpdate = () => {
    if (!apiClient.hasToken) {
      workbenchStore.patch({ updateStatus: "error" });
      return;
    }
    workbenchStore.patch({ updateStatus: "checking" });
    apiClient.checkUpdate()
      .then((result) => {
        workbenchStore.patch({
          updateStatus: result.available ? "available" : "up_to_date",
        });
      })
      .catch(() => workbenchStore.patch({ updateStatus: "error" }));
  };
  const prepareUpdate = () => {
    workbenchStore.patch({ updateStatus: "downloading" });
    apiClient.applyUpdate()
      .then((result) => {
        workbenchStore.patch({
          updateStatus: result.rollback
            ? "rollback"
            : result.status === "succeeded"
              ? "succeeded"
              : "available",
        });
      })
      .catch(() => workbenchStore.patch({ updateStatus: "error" }));
  };

  return (
    <div
      className="app-frame"
      style={{ gridTemplateColumns: sidebarWidth + "px minmax(0,1fr)" }}
      data-sidebar-collapsed={collapsed || undefined}
    >
      <Sidebar
        collapsed={collapsed}
        sidebarWidth={sidebarWidth}
        view={view}
        tools={tools}
        selectedTool={selectedTool}
        onToggle={toggleSidebar}
        onDragStart={onDragStart}
        onWorkbench={() => {
          workbenchStore.patch({ selectedTool: null });
          setView("workbench");
        }}
        onToolSelect={selectTool}
        onSettings={() => setView("settings")}
      />

      {/* ============ 主区 ============ */}
      <div className="sidebar-center-col">
        {view === "workbench" ? (
          <div className="workbench workbench-empty">
            <UpdateBanner
              status={updateStatus}
              onApply={prepareUpdate}
              onDismiss={() => workbenchStore.patch({ updateStatus: "idle" })}
            />
            <div className="empty-hero">
              <div className="empty-hero-icon">
                <LayoutGrid size={28} strokeWidth={1.4} />
              </div>
              <h2>{selectedToolDescriptor?.title ?? "工作台已就绪"}</h2>
              <p>{selectedToolDescriptor?.subtitle ?? "选择一个工具开始工作。"}</p>
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
                        <dd>DevBase</dd>
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
        <StatusBar
          connection={connection}
          version={APP_VERSION}
          onTogglePanel={toggleBottomPanel}
          onCheckUpdate={checkForUpdate}
          panelOpen={bottomPanelOpen}
        />
        {bottomPanelOpen && (
          <BottomPanel
            connection={connection}
            onClose={() => workbenchStore.patch({ bottomPanelOpen: false })}
          />
        )}
      </div>
    </div>
  );
}

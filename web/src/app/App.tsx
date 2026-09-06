import { useCallback, useEffect, useRef, useState } from "react";
import { LayoutGrid } from "lucide-react";

import { RuntimeEventStream } from "../api/events";
import { apiClient } from "../api/client";
import { BottomPanel } from "../components/BottomPanel";
import { DemoPanel } from "../components/DemoPanel";
import { Sidebar } from "../components/Sidebar";
import { StatusBar } from "../components/StatusBar";
import { SettingsView, type ThemeMode } from "../components/SettingsView";
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

const RAIL_WIDTH = 56;
const MIN_WIDE = 232;
const MAX_WIDE = 360;
const APP_VERSION = import.meta.env.VITE_APP_VERSION || "0.3.5";

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}

export default function App() {
  const [view, setView] = useState<View>("workbench");
  const [collapsed, setCollapsed] = useState(false);
  const [wideWidth, setWideWidth] = useState(264);
  const { tools, selectedTool, connection, bottomPanelOpen, updateStatus, events } = useWorkbenchStore();
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
      onSnapshot: (snapshot) => workbenchStore.setSnapshot(snapshot),
      onEvent: (event) => workbenchStore.pushEvent(event),
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
            {selectedToolDescriptor ? (
              <div className="empty-hero">
                <div className="empty-hero-icon">
                  <LayoutGrid size={28} strokeWidth={1.4} />
                </div>
                <h2>{selectedToolDescriptor.title}</h2>
                <p>{selectedToolDescriptor.subtitle ?? "选择一个工具开始工作。"}</p>
              </div>
            ) : (
              <DemoPanel sidebarCollapsed={collapsed} sidebarWidth={sidebarWidth} />
            )}
          </div>
        ) : (
          <SettingsView
            theme={theme}
            onThemeChange={setTheme}
            wideWidth={wideWidth}
            minWide={MIN_WIDE}
            maxWide={MAX_WIDE}
            onWideWidthChange={setWideWidth}
            version={APP_VERSION}
            onBack={() => setView("workbench")}
          />
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
            events={events}
            onClose={() => workbenchStore.patch({ bottomPanelOpen: false })}
          />
        )}
      </div>
    </div>
  );
}

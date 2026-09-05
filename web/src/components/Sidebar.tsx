import type { PointerEventHandler } from "react";
import {
  ArrowRight,
  BriefcaseBusiness,
  CircleHelp,
  LayoutGrid,
  MonitorCog,
  PanelLeft,
  Play,
  Settings,
  SlidersHorizontal,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { ToolDescriptor } from "../api/types";
import appLogo from "../assets/app-logo.svg";

export type SidebarView = "workbench" | "settings";

interface SidebarProps {
  collapsed: boolean;
  sidebarWidth: number;
  view: SidebarView;
  tools: ToolDescriptor[];
  selectedTool: string | null;
  onToggle: () => void;
  onDragStart: PointerEventHandler<HTMLDivElement>;
  onWorkbench: () => void;
  onToolSelect: (kind: string) => void;
  onSettings: () => void;
}

const glyphs: Record<string, LucideIcon> = {
  briefcase: BriefcaseBusiness,
  grid: LayoutGrid,
  monitor: MonitorCog,
  play: Play,
  settings: Settings,
  sliders: SlidersHorizontal,
  wrench: Wrench,
};

function ToolGlyph({ glyph }: { glyph: string }) {
  const Icon = glyphs[glyph] ?? Wrench;
  return <Icon size={18} strokeWidth={1.6} />;
}

export function Sidebar({
  collapsed,
  sidebarWidth,
  view,
  tools,
  selectedTool,
  onToggle,
  onDragStart,
  onWorkbench,
  onToolSelect,
  onSettings,
}: SidebarProps) {
  return (
    <>
      <nav
        className={`sidebar${collapsed ? " is-collapsed" : ""}`}
        aria-label="导航"
      >
        <div className="sidebar-brand-row">
          {!collapsed && (
            <button
              type="button"
              className="sidebar-brand"
              title="DevBase"
              onClick={onWorkbench}
            >
              <img className="sidebar-brand-mark" src={appLogo} alt="DevBase" />
              <span className="sidebar-brand-name">DevBase</span>
            </button>
          )}
          {collapsed && (
            <>
              <img className="sidebar-brand-mark" src={appLogo} alt="DevBase" title="DevBase" />
              <button
                type="button"
                className="sidebar-toggle sidebar-toggle-rail"
                aria-label="展开侧边栏"
                title="展开侧边栏"
                onClick={onToggle}
              >
                <ArrowRight size={18} strokeWidth={1.6} />
              </button>
            </>
          )}
          {!collapsed && (
            <button
              type="button"
              className="sidebar-toggle"
              aria-label="收起侧边栏"
              title="收起侧边栏"
              onClick={onToggle}
            >
              <PanelLeft size={16} strokeWidth={1.6} />
            </button>
          )}
        </div>

        <div className="sidebar-region" role="navigation">
          <ul className="sidebar-nav-list">
            <li>
              <button
                type="button"
                className={`sidebar-nav-item${view === "workbench" && selectedTool === null ? " is-selected" : ""}`}
                title="工作台"
                aria-current={view === "workbench" && selectedTool === null ? "page" : undefined}
                onClick={onWorkbench}
              >
                <span className="sidebar-nav-icon"><LayoutGrid size={18} strokeWidth={1.6} /></span>
                {!collapsed && (
                  <span className="sidebar-nav-text">
                    <span className="sidebar-nav-title">工作台</span>
                    <span className="sidebar-nav-sub">起始页</span>
                  </span>
                )}
              </button>
            </li>
            {tools.map((tool) => {
              const selected = view === "workbench" && selectedTool === tool.kind;
              return (
                <li key={tool.kind}>
                  <button
                    type="button"
                    className={`sidebar-nav-item${selected ? " is-selected" : ""}`}
                    title={tool.title}
                    aria-current={selected ? "page" : undefined}
                    onClick={() => onToolSelect(tool.kind)}
                  >
                    <span className="sidebar-nav-icon"><ToolGlyph glyph={tool.glyph} /></span>
                    {!collapsed && (
                      <span className="sidebar-nav-text">
                        <span className="sidebar-nav-title">{tool.title}</span>
                        <span className="sidebar-nav-sub">{tool.subtitle ?? tool.group}</span>
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="sidebar-foot">
          <button
            type="button"
            className={`sidebar-settings-btn${view === "settings" ? " is-active" : ""}`}
            title="设置"
            aria-label="设置"
            aria-current={view === "settings" ? "page" : undefined}
            onClick={onSettings}
          >
            <Settings size={collapsed ? 18 : 16} strokeWidth={1.6} />
            {!collapsed && <span className="sidebar-settings-label">设置</span>}
          </button>
          {!collapsed && <CircleHelp className="sidebar-help-icon" size={15} strokeWidth={1.6} />}
        </div>
      </nav>
      {!collapsed && (
        <div
          className="sidebar-drag-handle"
          style={{ left: sidebarWidth - 4 }}
          onPointerDown={onDragStart}
          aria-hidden="true"
        />
      )}
    </>
  );
}

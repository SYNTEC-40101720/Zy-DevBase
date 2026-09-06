import { ArrowLeft, LayoutGrid, Monitor, Moon, Sun } from "lucide-react";

export type ThemeMode = "system" | "light" | "dark";

interface SettingsViewProps {
  theme: ThemeMode;
  onThemeChange: (theme: ThemeMode) => void;
  wideWidth: number;
  minWide: number;
  maxWide: number;
  onWideWidthChange: (width: number) => void;
  version: string;
  onBack: () => void;
}

export function SettingsView({
  theme,
  onThemeChange,
  wideWidth,
  minWide,
  maxWide,
  onWideWidthChange,
  version,
  onBack,
}: SettingsViewProps) {
  const themeOptions = [
    { id: "system", label: "跟随系统", icon: <Monitor size={15} strokeWidth={1.6} /> },
    { id: "light", label: "浅色", icon: <Sun size={15} strokeWidth={1.6} /> },
    { id: "dark", label: "暗色", icon: <Moon size={15} strokeWidth={1.6} /> },
  ] as const;

  return (
    <div className="workbench settings-view">
      <header className="settings-view-header">
        <button
          type="button"
          className="settings-view-back"
          aria-label="返回工作台"
          title="返回工作台"
          onClick={onBack}
        >
          <ArrowLeft size={18} strokeWidth={1.6} />
        </button>
        <h2 className="settings-view-title">设置</h2>
      </header>
      <div className="settings-view-body">
        <div className="settings-scroll">
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
                  {themeOptions.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      className={"theme-option" + (theme === option.id ? " is-selected" : "")}
                      role="radio"
                      aria-checked={theme === option.id}
                      onClick={() => onThemeChange(option.id)}
                    >
                      {option.icon}
                      <span>{option.label}</span>
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
                  min={minWide}
                  max={maxWide}
                  step={1}
                  value={wideWidth}
                  onChange={(event) => onWideWidthChange(Number(event.target.value))}
                  aria-label="侧边栏宽度"
                />
                <div className="settings-range-ticks">
                  <span>窄</span>
                  <span>宽</span>
                </div>
              </div>
            </div>
          </section>

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
                  <dd>{version}</dd>
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
  );
}

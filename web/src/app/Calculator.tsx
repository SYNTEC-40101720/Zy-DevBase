import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { Delete, History, X } from "lucide-react";

import { fetchCalcState, pressCalcKey } from "../api/client";
import type { CalcState } from "../api/types";

/* ============================================================
 *  计算器工作台 — 按 Microsoft Calculator (Fluent) 重构
 *  - 标题栏：汉堡菜单 + 模式名 + 历史开关
 *  - 显示区：表达式小字 + 大号右对齐结果 + M 标记
 *  - 内存行：MC / MR / M+ / M− / MS（扁平小按钮，满宽）
 *  - 主键盘：6 行 × 4 列，与 Windows 标准模式按键一致
 *  - 历史侧栏：按时间倒序
 *  - 键盘支持
 * ============================================================ */

type Variant = "num" | "binop" | "fn" | "mem" | "eq" | "clear" | "back";

interface KeyDef {
  label: ReactNode;
  key: string;
  variant: Variant;
  aria?: string;
}

/* 标准模式主键盘：6 行 × 4 列（与 Windows 计算器一致） */
const PAD: KeyDef[][] = [
  [
    { label: "%",   key: "%",     variant: "fn" },
    { label: "CE",  key: "CE",    variant: "clear" },
    { label: "C",   key: "C",     variant: "clear" },
    { label: <Delete size={18} strokeWidth={1.6} />, key: "back", variant: "back", aria: "退格" },
  ],
  [
    { label: "¹⁄ₓ",  key: "1/x",  variant: "fn", aria: "倒数" },
    { label: "x²",  key: "x²",   variant: "fn", aria: "平方" },
    { label: "√x",  key: "sqrt", variant: "fn", aria: "平方根" },
    { label: "÷",   key: "/",    variant: "binop", aria: "除以" },
  ],
  [
    { label: "7", key: "7", variant: "num" },
    { label: "8", key: "8", variant: "num" },
    { label: "9", key: "9", variant: "num" },
    { label: "×", key: "*", variant: "binop", aria: "乘以" },
  ],
  [
    { label: "4", key: "4", variant: "num" },
    { label: "5", key: "5", variant: "num" },
    { label: "6", key: "6", variant: "num" },
    { label: "−", key: "-", variant: "binop", aria: "减" },
  ],
  [
    { label: "1", key: "1", variant: "num" },
    { label: "2", key: "2", variant: "num" },
    { label: "3", key: "3", variant: "num" },
    { label: "+", key: "+", variant: "binop", aria: "加" },
  ],
  [
    { label: "±", key: "+/-", variant: "num", aria: "正负号" },
    { label: "0", key: "0", variant: "num" },
    { label: ".", key: ".", variant: "num", aria: "小数点" },
    { label: "=", key: "=", variant: "eq", aria: "等于" },
  ],
];

/* 内存行：满宽均分 5 枚 */
const MEM_ROW: KeyDef[] = [
  { label: "MC", key: "MC", variant: "mem" },
  { label: "MR", key: "MR", variant: "mem" },
  { label: "M+", key: "M+", variant: "mem" },
  { label: "M−", key: "M-", variant: "mem" },
  { label: "MS", key: "MS", variant: "mem" },
];

// 键盘 -> 计算器按键映射
const KEY_MAP: Record<string, string> = {
  "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
  "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
  ".": ".", ",": ".",
  "+": "+", "-": "-", "*": "*", "/": "/",
  "x": "*", "X": "*",
  Enter: "=", "=": "=",
  Escape: "C",
  Backspace: "back",
  "%": "%",
  "@": "sqrt",
};

const EMPTY_STATE: CalcState = {
  display: "0",
  expression: [],
  error: false,
  memory: [],
  history: [],
};

interface CalculatorProps {
  onToggleNav: () => void;
}

export default function Calculator({ onToggleNav }: CalculatorProps) {
  const [state, setState] = useState<CalcState>(EMPTY_STATE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const historyRef = useRef<HTMLDivElement | null>(null);

  // 初始加载
  useEffect(() => {
    let disposed = false;
    fetchCalcState()
      .then((s) => { if (!disposed) setState(s); })
      .catch(() => {});
    return () => { disposed = true; };
  }, []);

  // 历史栏置顶最新
  useEffect(() => {
    const el = historyRef.current;
    if (el) el.scrollTop = 0;
  }, [state.history, historyOpen]);

  const press = useCallback(async (key: string) => {
    if (!key || loading) return;
    setLoading(true);
    setError(null);
    try {
      const next = await pressCalcKey(key);
      setState(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "按键失败");
    } finally {
      setLoading(false);
    }
  }, [loading]);

  // 键盘
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
      const mapped = KEY_MAP[e.key];
      if (!mapped) return;
      e.preventDefault();
      void press(mapped);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [press]);

  const expressionText = state.expression.join(" ");
  const hasMemory = state.memory.length > 0;

  const renderKey = (k: KeyDef, i: number) => (
    <button
      key={i}
      type="button"
      className={"calc-key is-" + k.variant + (loading ? " is-disabled" : "")}
      disabled={loading}
      aria-label={k.aria ?? (typeof k.label === "string" ? k.label : undefined)}
      onClick={() => void press(k.key)}
    >
      {k.label}
    </button>
  );

  const historyItems = [...state.history].reverse();
  const shellClass = "calc-shell" + (historyOpen ? " has-flyout" : "");
  const displayClass = "calc-display" + (state.error ? " is-error" : "");

  return (
    <div className="workbench calc-workbench">
      {/* ---- 标题栏 ---- */}
      <header className="calc-titlebar">
        <button
          type="button"
          className="calc-hamburger"
          aria-label="切换侧边栏"
          title="切换侧边栏"
          onClick={onToggleNav}
        >
          <span className="calc-hamburger-lines" aria-hidden="true" />
        </button>
        <span className="calc-mode-title">标准</span>
        <div className="calc-titlebar-actions">
          <button
            type="button"
            className={"calc-toggle" + (historyOpen ? " is-on" : "")}
            aria-pressed={historyOpen}
            aria-label="历史记录"
            title="历史记录"
            onClick={() => setHistoryOpen((v) => !v)}
          >
            <History size={17} strokeWidth={1.6} />
          </button>
        </div>
      </header>

      <div className="calc-stage">
        <div className={shellClass}>
          {/* ---- 显示区 ---- */}
          <div className={displayClass}>
            {hasMemory && (
              <span className="calc-mem-pill" aria-label="内存非空">M</span>
            )}
            <div className="calc-expression" aria-live="polite">
              {expressionText || " "}
            </div>
            <div className="calc-readout" aria-live="polite">
              {state.display}
            </div>
          </div>

          {/* ---- 内存行 ---- */}
          <div className="calc-memrow" role="group" aria-label="内存操作">
            {MEM_ROW.map(renderKey)}
          </div>

          {error && <div className="calc-error" role="alert">{error}</div>}

          {/* ---- 主键盘 ---- */}
          <div className="calc-pad" role="group" aria-label="按键">
            {PAD.flat().map(renderKey)}
          </div>

          {/* ---- 历史侧栏 ---- */}
          {historyOpen && (
            <aside className="calc-history-flyout" aria-label="历史记录">
              <div className="calc-flyout-head">
                <span>历史记录</span>
                <button
                  type="button"
                  className="calc-flyout-close"
                  aria-label="关闭历史记录"
                  onClick={() => setHistoryOpen(false)}
                >
                  <X size={15} strokeWidth={1.6} />
                </button>
              </div>
              <div className="calc-history-list" ref={historyRef}>
                {historyItems.length === 0 ? (
                  <p className="calc-history-empty">尚无历史记录</p>
                ) : (
                  historyItems.map((h, i) => (
                    <button
                      type="button"
                      key={i}
                      className="calc-history-item"
                      aria-label={h.expression + " = " + h.result}
                    >
                      <span className="calc-history-expr">{h.expression}&nbsp;=</span>
                      <span className="calc-history-result">{h.result}</span>
                    </button>
                  ))
                )}
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

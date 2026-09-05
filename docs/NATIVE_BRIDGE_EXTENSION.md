# NativeBridge 扩展指南

> Issue #7 验收项：扩展模式文档说明如何添加业务方法

## 概述

`NativeBridge` 是 DevBase 暴露给前端 JavaScript 的 Python↔JS 桥梁。
它只包含**业务无关**的通用方法（目录选择、目录打开、运行时信息）。

派生项目（如发票处理系统）需要添加业务专属方法（如 `select_pdf_files()`、
`save_log_dialog()`、`write_log(content)`），应遵循以下扩展模式。

---

## 扩展模式

### 原则

1. **不修改 DevBase 基类** — 派生项目创建子类或组合，不改动 `native_bridge.py`
2. **方法名用 `@window.expose` 装饰** — 否则前端 JS 无法调用
3. **返回 JSON 可序列化值** — pywebview 通过 JSON 序列化传值
4. **业务回调用注入** — 目录选择器、打开器等通过构造函数注入，便于测试

### 方式一：子类继承（推荐）

```python
from devbase.desktop.native_bridge import NativeBridge
from pathlib import Path


class InvoiceNativeBridge(NativeBridge):
    """发票项目的 NativeBridge 扩展。"""

    def select_pdf_files(self, title: str = "选择发票 PDF") -> list[str]:
        """打开文件选择器，仅允许选择 PDF 文件。"""
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        try:
            files = filedialog.askopenfilenames(
                title=title,
                filetypes=[("PDF files", "*.pdf")],
            )
            return list(files) if files else []
        finally:
            root.destroy()

    def save_log_dialog(self, default_name: str = "log.txt") -> str | None:
        """打开保存对话框，返回用户选择的保存路径。"""
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        try:
            path = filedialog.asksaveasfilename(
                title="保存日志",
                defaultextension=".txt",
                initialfile=default_name,
            )
            return path or None
        finally:
            root.destroy()

    def write_log(self, path: str, content: str) -> bool:
        """将内容写入指定路径的日志文件。"""
        try:
            Path(path).write_text(content, encoding="utf-8")
            return True
        except OSError:
            return False
```

### 方式二：组合注入（适配器模式）

适合需要在多个项目间复用业务方法的场景：

```python
from devbase.desktop.native_bridge import NativeBridge


class InvoiceBridgeAdapter:
    """将业务方法委托给独立模块，保持 NativeBridge 不被污染。"""

    def __init__(self, base: NativeBridge):
        self._base = base  # 通用方法委托给基类
        # 业务专属方法直接实现
        self._log_path = None

    def select_directory(self, title: str = "选择发票文件夹") -> str | None:
        return self._base.select_directory(title=title)

    def get_runtime_info(self) -> dict:
        return self._base.get_runtime_info()

    def select_pdf_files(self) -> list[str]:
        # 业务逻辑...
        pass
```

### 在 Launcher 中注册扩展 Bridge

```python
from devbase.desktop.launcher import Launcher
from my_project.invoice_native_bridge import InvoiceNativeBridge

launcher = Launcher()
# 覆盖默认的 NativeBridge
launcher._native_bridge = InvoiceNativeBridge()
launcher.start()
```

pywebview 会自动将 `NativeBridge` 子类中所有公开方法暴露到
`window.pywebview.api` 对象上。

---

## 前端调用扩展方法

```typescript
// 在 React 组件中调用扩展方法
const handleSelectPdf = async () => {
  const files = await window.pywebview.api.select_pdf_files();
  console.log("Selected PDFs:", files);
};

// 通用方法仍然可用
const handleSelectDirectory = async () => {
  const dir = await window.pywebview.api.select_directory("选择输出目录");
  if (dir) {
    console.log("Selected:", dir);
  }
};
```

---

## 测试扩展方法

```python
from pathlib import Path
from my_project.invoice_native_bridge import InvoiceNativeBridge


def test_write_log_creates_file(tmp_path: Path) -> None:
    bridge = InvoiceNativeBridge()
    result = bridge.write_log(str(tmp_path / "log.txt"), "hello")
    assert result is True
    assert (tmp_path / "log.txt").read_text() == "hello"
```

---

## 注意事项

- **不要硬编码路径**：使用 `select_directory(title=...)` 的 `title`
  参数来区分不同场景，不要在 `NativeBridge` 级别硬编码
- **`open_directory` 回调验证**：使用 `checker` 回调验证目录打开后仍然存在
  （用户可能在打开后删除目录）
- **线程安全**：pywebview 的 JS↔Python 调用是异步的，确保业务方法
  本身是线程安全的
- **返回值类型**：只返回 str/int/float/bool/list/dict/None 等 JSON 可序列化类型

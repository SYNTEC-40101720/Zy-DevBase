# Python Web Desktop Platform Template

这是开发体系的隔离试验场，不参与当前发票系统的运行和打包。

## 当前边界

- 现有发票项目仍位于仓库根目录，作为参考实现，不在这里直接重构。
- 新工具默认采用 Python + FastAPI + React/TypeScript，并以 pywebview/WebView2 作为 Windows 桌面壳；浏览器模式只用于开发调试。
- 默认适配离线、受限 Windows 环境，不依赖 Redis、Celery 或外部数据库服务。
- 每个工具独立发布；后续通过稳定契约和公共包接入统一工作台。
- 任务状态默认驻留内存，窗口关闭行为由具体工具配置。

## 当前模板结构

```text
platform_template/
├─ main.py              # 模板根目录后端启动入口
├─ backend/
│  ├─ pyproject.toml
│  ├─ platform_runtime/
│  │  ├─ domain/          # 任务和事件模型
│  │  ├─ application/     # 内存运行时、事件总线、生命周期策略
│  │  ├─ api/             # /api/v1 HTTP 与 WebSocket
│  │  └─ desktop/         # 可选 pywebview/WebView2 适配
│  └─ tests/              # 运行时和 API 窄测试
└─ web/
	├─ package.json
	├─ package-lock.json
	├─ vite.config.ts
	└─ src/                 # React/TypeScript 最小工作台
```

后端包名是 `platform_runtime`，不复用仓库根目录的 `src`。演示任务只允许一个非终态任务并使用线程和内存状态；进度事件可合并，关键生命周期事件会优先保留在重放窗口内。桌面模式默认通过 `WindowLifecycle` 使用 `stop_on_close`，窗口关闭时取消活动任务并退出本地服务；浏览器调试模式不负责桌面窗口生命周期。

事件重放历史默认保留最近 512 个事件，历史超出范围后以当前任务快照作为恢复依据；需要完整审计记录的工具应另行接入持久化适配器。

## 本地开发

后端需要 Python 3.12，前端需要 Node.js 18+。PowerShell 中从模板目录执行：

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test,desktop]"
python -m pytest
```

如果只运行 API 测试、不启动桌面窗口，可以只安装测试依赖：

```powershell
python -m pip install -e ".[test]"
```

目标 Windows 环境需要安装 WebView2 Runtime。

先构建前端，再从模板根目录启动默认的独立桌面界面：

```powershell
cd ..
cd web
npm ci
npm run typecheck
npm run build
cd ..
python main.py
```

`main.py` 默认使用 pywebview/WebView2 托管 `web/dist`，服务就绪后打开独立工具窗口。`python main.py --desktop` 是显式的等价写法。可以继续使用 `--host`、`--port`，或通过 `PLATFORM_HOST`、`PLATFORM_PORT` 设置默认监听地址。若缺少 `web/dist/index.html`，入口会提示先在 `web` 执行 `npm ci` 和 `npm run build`。

浏览器模式只用于开发调试：

```powershell
python main.py --browser
python main.py --browser --reload
```

`--reload` 只能和 `--browser` 一起使用；`--no-browser` 只在浏览器模式下阻止自动打开外部浏览器：

```powershell
python main.py --browser --no-browser
```

桌面模式不会打开外部浏览器；即使传入 `--no-browser` 也不影响 WebView 窗口。当前是源码运行的独立窗口，不代表已经完成 PyInstaller EXE 打包。

需要前端热更新时，另开终端启动 Vite 开发服务器：

```powershell
cd web
npm run dev
```

Vite 开发服务器默认在 `http://127.0.0.1:5173`，会把 `/api` 和 WebSocket 请求代理到 `127.0.0.1:8000`。也可以使用 `VITE_API_BASE_URL` 和 `VITE_WS_URL` 指向其他本地服务。

## 有意留下的边界

- 这里没有数据库、Redis、Celery 或其他外部服务。
- 这里没有业务模块，演示任务只用于验证生命周期和事件契约。
- 桌面模式已提供 pywebview/WebView2 适配，但没有实现 Native Bridge，也没有完成 PyInstaller EXE 打包；当前只是源码运行的独立窗口。适配新业务工具时，只需替换业务模块、传入窗口标题和尺寸，并按需增加 Native Bridge，不要复制仓库根目录的发票业务代码。
- 初始化阶段不抽取公共包。等多个独立工具验证契约稳定后，再整体剪切模板并沉淀共享能力。

## 迭代顺序

1. 从当前项目提取最小通用骨架。
2. 抽象任务执行、事件总线、生命周期和桌面桥接接口。
3. 加入一个不含发票业务的示例工具。
4. 建立 Python、Web、桌面打包和验收测试。
5. 稳定后整体剪切到独立仓库。

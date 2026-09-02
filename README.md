# Zy_DevBase

Windows 本地桌面工具的基础项目骨架。复制即可开新工具，不用从零搭起。

## 技术栈

- **后端**：Python 3.12 + FastAPI + Pydantic + Uvicorn
- **前端**：React 19 + TypeScript + Vite 6
- **桌面壳**：pywebview / WebView2（Windows）
- **测试**：pytest + httpx（后端）、tsc（前端）

默认适配离线、受限 Windows 环境，不依赖 Redis、Celery 或外部数据库服务。任务状态默认驻留内存。

## 目录结构

```text
Zy_DevBase/
├─ main.py                 # 启动入口：桌面 / 浏览器双模式
├─ backend/
│  ├─ pyproject.toml
│  ├─ zy_devbase/
│  │  ├─ domain/           # 任务状态机、领域事件（零 web 依赖）
│  │  ├─ application/       # 内存运行时、事件总线、生命周期策略
│  │  ├─ api/              # /api/v1 HTTP 与 WebSocket
│  │  └─ desktop/          # pywebview / WebView2 桌面适配
│  └─ tests/               # 运行时、API、桌面适配测试
└─ web/
   ├─ package.json
   ├─ vite.config.ts
   └─ src/                  # React / TypeScript 工作台
```

### 后端分层

| 层 | 职责 | 依赖 |
| --- | --- | --- |
| `domain` | 任务状态机、领域事件值对象、**端口契约**（`ProgressSink`/`DisplaySink`）、**资源提供者** | 无框架依赖 |
| `application` | 内存运行时、事件总线、窗口生命周期、**声明式工具清单**（`ToolRegistry`/`ToolDescriptor`） | 仅依赖 `domain` |
| `api` | FastAPI 工厂、路由、Pydantic 契约 | 依赖 `application` |
| `desktop` | pywebview 窗口、本地服务托管 | 依赖 `api` |

业务核心在 `domain` 和 `application`，不绑定 FastAPI 或 pywebview，可独立单元测试。换新业务时只改这两层，`api` / `desktop` / 前端骨架不动。

> 架构思路借鉴自微软开源 Windows 计算器（`Microsoft/calculator`）的端口/清单模式：引擎在 `domain` 声明它需要的**端口**，宿主在 `application` 实现；工具以**声明式清单**注册（对应其 `NavCategoryStates.CategoryManifest`），前端导航栏从清单渲染；用户可见字符串走**资源提供者**，逻辑内不硬编码本地化文本。

### 前端骨架

前端是一个纯外壳：侧边栏（可拖拽调宽、折叠为 rail、悬停揭示展开）、工作台空态起始页、内联设置页（主题切换 + 侧边栏宽度调节）。不包含任何业务视图——作为模板，后续按需在 `web/src/app/` 添加工具视图。

## 本地开发

### 后端

需要 Python 3.12。PowerShell 从模板根目录执行：

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test,desktop]"
python -m pytest -q
```

只跑 API 测试、不启动桌面窗口时，可只装测试依赖：

```powershell
python -m pip install -e ".[test]"
```

### 前端

需要 Node.js 18+：

```powershell
cd web
npm ci
npm run typecheck
npm run build
```

### 启动

先构建前端，再从模板根目录启动：

```powershell
python main.py
```

`main.py` 默认用 pywebview / WebView2 托管 `web/dist`，服务就绪后打开独立桌面窗口。`python main.py --desktop` 是显式等价写法。支持 `--host`、`--port`，或通过 `PLATFORM_HOST`、`PLATFORM_PORT` 设置默认监听地址。缺少 `web/dist/index.html` 时会提示先构建前端。

浏览器调试模式：

```powershell
python main.py --browser
python main.py --browser --reload     # 热更新，仅限浏览器模式
python main.py --browser --no-browser  # 不自动开浏览器
```

前端热更新时另开终端：

```powershell
cd web
npm run dev
```

Vite 开发服务器默认在 `http://localhost:5173`，会把 `/api` 和 WebSocket 请求代理到 `localhost:8000`。

## API

后端 API 前缀 `/api/v1`：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查 |
| GET | `/jobs/current` | 当前任务快照 |
| POST | `/jobs/start` | 启动任务（按 `kind` 查清单） |
| POST | `/jobs/cancel` | 取消当前任务 |
| WS | `/events` | 事件流（含重放） |
| GET | `/tools` | 已注册工具清单（供前端导航渲染） |

运行时只允许一个非终态任务。任务通过后台线程执行，支持完成、取消、冲突检测和失败状态。事件总线合并相邻的同任务进度事件，重放历史默认最多 512 个事件；重连时以当前任务快照为权威状态。

`/tools` 返回 `ToolRegistry` 中所有 `ToolDescriptor`，前端可据此渲染导航栏。

## 扩展新工具

1. 替换 `domain/` 和 `application/` 里的业务逻辑（任务、事件、状态机）
2. 在 `api/routes/` 增改路由，在 `api/schemas.py` 调整响应模型
3. 在 `web/src/app/` 添加工具视图，在 `App.tsx` 导航列表注册
4. 调 `main.py` 和 `desktop/launcher.py` 的窗口标题、尺寸
5. 不动 `event_bus` / `desktop` 骨架，除非确有需要

## 边界

- 无数据库、Redis、Celery 或其他外部服务
- 无业务模块，演示任务只验证运行时契约
- 已提供 pywebview / WebView2 桌面壳，未实现 Native Bridge 和 PyInstaller EXE 打包
- 无账号、权限和局域网安全边界，当前只面向本机开发服务
- 任务状态默认不持久化，进程重启后丢失

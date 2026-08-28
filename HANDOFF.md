# 平台模板交接文档

更新时间：2026-08-28

## 1. 这是什么

`platform_template/` 是从当前发票项目旁边建立的开发体系试验场。它的目标是验证一套可以复制到新工具的基础组合：

- Python 负责领域逻辑、任务执行和服务端 API。
- FastAPI + Pydantic 负责本地服务和稳定数据契约。
- React + TypeScript + Vite 负责复杂 Web 工作台。
- 默认通过可选的 pywebview + WebView2 打开 Windows 独立桌面窗口；本地浏览器模式只用于开发调试。

当前发票项目仍在仓库根目录，是参考实现；本模板不依赖根目录的 `src`，也不包含发票业务。剪切时应整体移动 `platform_template/`，不要把根目录的源码混入模板。

## 2. 已确认的产品与架构决策

这些决策来自模板建立前的逐项确认，后续调整时应明确记录新的决策，不要默认推翻它们。

| 事项 | 当前结论 |
| --- | --- |
| 首要形态 | Windows 本地桌面单用户，同时作为未来内部工具的样板 |
| 界面复杂度 | 暂不预设，优先统一技术栈和长期维护成本 |
| 技术边界 | Python 负责业务和服务端；复杂界面使用 React + TypeScript |
| 远程访问 | 当前不需要，但 API、应用层和领域层不要绑定桌面壳，未来可转局域网 Web |
| 任务持久化 | 默认不持久化；进程重启后任务和事件状态丢失 |
| 窗口关闭 | 由具体工具选择 `stop_on_close` 或 `continue_on_close` |
| 工具组织 | 先独立开发和独立发布，未来可接入统一工作台 |
| 外部服务 | 默认适应离线、受限 Windows，不要求 Redis、Celery 或数据库服务 |
| 复用方式 | 先用项目模板初始化，稳定能力再沉淀为版本化公共包 |

## 3. 当前实现

```text
platform_template/
├─ main.py
├─ HANDOFF.md
├─ README.md
├─ .gitignore
├─ backend/
│  ├─ pyproject.toml
│  ├─ platform_runtime/
│  │  ├─ domain/
│  │  │  ├─ job.py             # 任务状态和值对象
│  │  │  └─ events.py          # 事件类型和值对象
│  │  ├─ application/
│  │  │  ├─ job_runtime.py     # 单任务内存运行时和演示任务
│  │  │  ├─ event_bus.py       # 线程安全事件历史和进度合并
│  │  │  ├─ lifecycle.py       # 窗口关闭策略边界
│  │  │  └─ errors.py           # 应用层错误
│  │  ├─ api/
│  │  │  ├─ app.py             # FastAPI 工厂和依赖注入
│  │  │  ├─ schemas.py         # Pydantic 响应模型
│  │  │  └─ routes/             # health、jobs、events 路由
│  │  ├─ desktop/
│  │  │  ├─ __init__.py
│  │  │  └─ launcher.py         # pywebview/WebView2 桌面适配
│  │  └─ __main__.py            # 直接启动 Uvicorn
│  └─ tests/
│     ├─ test_runtime.py
│     └─ test_api.py
└─ web/
   ├─ package.json
   ├─ package-lock.json
   ├─ vite.config.ts
   └─ src/
      ├─ api/                   # HTTP、WebSocket 和类型
      ├─ app/App.tsx            # 最小工作台
      └─ styles/                # 视觉 token 和工作台布局
```

桌面适配位于 `backend/platform_runtime/desktop/launcher.py`，其窄测试位于 `backend/tests/test_desktop_launcher.py`；两者都不引入业务逻辑或 Native Bridge。

当前后端 API 前缀是 `/api/v1`，包含：

- `GET /health`
- `GET /jobs/current`
- `POST /jobs/start`
- `POST /jobs/cancel`
- `WS /events`

运行时只允许一个非终态任务。演示任务通过后台线程执行，支持完成、取消、重复启动冲突和失败状态。事件总线会合并相邻的同任务进度事件，重放历史默认最多保留 512 个事件；重连时以当前任务快照为权威状态。

窗口生命周期已经抽象为 `WindowLifecycle`，支持 `stop_on_close` 和 `continue_on_close`。桌面启动器默认注入 `stop_on_close`，浏览器调试模式不负责桌面窗口生命周期。桌面适配器只负责启动本地服务、承载 WebView 和处理关闭信号，不包含业务任务逻辑。

## 4. 独立运行

PowerShell 从 `platform_template/` 开始：

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test,desktop]"
python -m pytest -q
```

如果只运行 API 测试、不启动桌面窗口，可以只安装测试依赖：

```powershell
python -m pip install -e ".[test]"
```

目标 Windows 环境需要 WebView2 Runtime。

标准本地闭环是先构建前端，再从模板根目录启动默认桌面模式：

```powershell
cd ..
cd web
npm ci
npm run typecheck
npm run build
cd ..
python main.py
```

`main.py` 默认使用 pywebview/WebView2 托管 `web/dist` 并打开独立工具窗口；`--desktop` 是显式的等价写法。支持 `--host` 和 `--port`；缺少 `web/dist/index.html` 时会明确提示先在 `web` 执行 `npm ci` 和 `npm run build`。需要前端热更新时，可以另开终端运行 `npm run dev`。

浏览器调试模式：

```powershell
python main.py --browser
python main.py --browser --reload
python main.py --browser --no-browser
```

桌面模式使用同一个静态 FastAPI 应用，等待 `/api/v1/health` 就绪后打开 WebView2 窗口，不启动外部浏览器。浏览器模式只用于调试；`--reload` 只能和 `--browser` 一起使用，`--no-browser` 只影响浏览器模式。桌面启动器的 `window_title`、`window_width` 和 `window_height` 参数是新工具调整标题和尺寸的入口；当前没有 Native Bridge，也没有完成 PyInstaller EXE 打包。

另开终端启动前端：

```powershell
cd web
npm ci
npm run typecheck
npm run dev
```

前端开发地址默认是 `http://127.0.0.1:5173`，Vite 会将 `/api` 和 WebSocket 请求代理到 `127.0.0.1:8000`。生产构建命令是：

```powershell
npm run build
```

生成的 `web/dist/` 属于构建产物，不应作为源码提交；`.gitignore` 已覆盖它和 `node_modules/`。

## 5. 剪切到独立仓库

建议在模板完成第一轮示例工具后再剪切。剪切步骤：

```powershell
git status --short
 目标 Windows 环境需要安装 WebView2 Runtime；前端构建需要 Node.js 18+。
cd backend
 从 `backend` 执行 `python -m pytest -q`：12 项通过，包含不启动真实 GUI 的桌面适配测试。
cd ..\web
 在不包含缓存和依赖目录的临时独立副本中执行 `python -m pytest -q`、`npm ci`、`npm run typecheck` 和 `npm run build`：通过。
```
 健康接口和 WebSocket 初始消息会返回实际的 `window_close_mode`，桌面与浏览器模式分别验证通过。
 浏览器模式的自定义主机、通配地址和 IPv6 URL 规范化：通过。

在原仓库的 `platform_template/` 目录内已验证：

- 从 `backend` 执行 `python -m pytest -q`：11 项通过，包含不启动真实 GUI 的桌面适配测试。
- `python -m compileall -q platform_template`：通过。
- `npm run typecheck`：通过。
- `npm run build`：通过。
- `python main.py --help`：通过，不启动服务。
- `python main.py` 的参数解析默认为桌面模式；`--browser --reload` 进入浏览器调试模式。
- 默认桌面模式与 `--reload` 组合：按预期由参数解析器拒绝并给出中文提示。
- 真实入口冒烟：`--no-browser` 启动后 `/api/v1/health` 和 `/` 均返回 200，服务退出完成。
- `--reload --no-browser` 短测：启动和应用关闭完成，未出现 Uvicorn 工厂警告。
- VS Code 诊断：无错误。

当前环境没有安装 `ruff`，因此没有执行 Ruff 检查。若将模板作为独立仓库维护，应把 Ruff 纳入开发依赖或 CI。

## 7. 明确未完成的部分

- 已实现可选的 pywebview/WebView2 桌面壳，但尚未实现 Native Bridge 和 PyInstaller 打包；不要将模板描述为已经打包成 EXE。
- 尚未实现持久化任务历史、崩溃恢复和完整审计日志。
- 尚未实现账号、权限和局域网部署安全边界；当前默认只面向本机开发服务。
- 尚未实现真正的示例业务工具，当前演示任务只用于验证运行时契约。
- `continue_on_close` 只表示桌面窗口回调不主动取消任务；如果整个 Python 进程退出，后台线程也会结束，不能把它误解为跨进程续跑。
- 事件重放历史是有界的；需要完整历史的工具必须增加持久化适配器，不能依赖内存事件总线。

## 8. 推荐的下一轮顺序

1. 创建一个不含发票规则的文件批处理示例，验证业务模块如何接入任务运行时。
2. 将任务执行器、事件总线和生命周期策略的接口边界补成可替换协议。
3. 在具体工具中验证 pywebview/WebView2、中文路径、DPI、关闭回调和静态资源加载。
4. 增加模板级打包脚本和 Windows 启动冒烟测试。
5. 用第二个独立小工具验证模板复制流程；重复出现的稳定代码再提取为公共包。

## 9. 后续协作规则

恢复工作时先阅读本文件和 `README.md`，再运行后端测试与前端构建。默认只修改 `platform_template/`；只有用户明确要求把能力回迁到发票项目时，才进入仓库根目录的现有实现。每次跨边界改动都应在本文件的“当前实现”“验证记录”或“未完成部分”中留下简短记录。

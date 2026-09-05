# DevBase 基础框架升级任务清单

> 执行仓库：`SYNTEC-40101720/Zy-DevBase`
>
> 目标：把发票项目中已验证的通用能力沉淀到 DevBase，作为后续 SYNTEC Windows 桌面工具的基础轮子。
>
> 规则：每完成一个任务，先运行该任务的最窄验证，再进入下一项；不要把发票业务代码放进 DevBase。

## 当前状态

- [x] 迁移决策已确认
- [x] 迁移 SOP 已整理
- [x] 当前安全层代码语法验证通过
- [x] 当前 API 测试已同步 token 契约并通过
- [x] 任务 1（安全层：Token、Origin、CSP）已完成，15 项测试通过
- [x] 任务 2（完整双模式启动）已完成，新增 21 项 launcher 测试
- [x] 任务 3（领域端口契约）已确认满足，7 项测试通过
- [x] 任务 4（运行时和状态机统一）已完成，新增 JobPhase/JobTrigger + CANCELLING 中间态
- [x] 任务 5（资源提供者）已确认满足，7 项测试通过
- [x] 任务 6（事件总线融合）已完成，新增 10 项事件总线测试
- [x] 任务 7（通用日志配置）已完成，新增 11 项日志配置测试
- [x] 任务 8（Task 与 ToolRegistry）已完成，补充重复注册保护和未知任务 404
- [x] 任务 9（窗口生命周期）已完成，补充运行中/终态任务及继续模式等待测试
- [x] 任务 10（通用配置与 DPAPI）已完成，新增 14 项配置/secret store 测试
- [x] 任务 11（版本同步工具）已完成，支持 bump/sync/check 和 Windows 四元组
- [x] 任务 12（通用 NativeBridge）已完成，接入 pywebview js_api 并新增平台替身测试
- [x] 任务 13（前端共享组件）已完成，新增 API/WebSocket/store/状态组件并通过构建
- [x] 任务 14（.spec 打包与构建脚本）已完成，主程序和独立 updater 均已打包
- [x] 任务 15（GitHub Release 自动更新）已完成核心实现、测试和更新 SOP
- [x] P0-P3 基础升级任务已实施；真实 GitHub Release 和干净域控替换冒烟仍需发布环境执行

当前未提交改动：

- `backend/devbase/api/app.py`
- `backend/devbase/api/dependencies.py`
- `backend/devbase/api/routes/events.py`
- `backend/devbase/api/routes/jobs.py`
- `backend/devbase/api/routes/system.py`
- `backend/devbase/api/routes/tools.py`

## 开始前

```powershell
cd D:\FN\Zy-DevBase
backend\.venv\Scripts\Activate.ps1
python -m pytest -q
cd web
npm run typecheck
npm run build
cd ..
```

当前起点结果：`python -m compileall -q devbase` 和 `tests/test_api.py` 已通过。第 1 项仍需补充 Origin、错误 token、OpenAPI 和安全响应头的完整覆盖。

## P0：基础运行能力

### 1. 完成安全层：Token、Origin、CSP

来源：发票项目 `src/api/app.py`、`src/api/dependencies.py`。

- [x] `create_app()` 支持显式 `local_token`，未传时自动生成随机 token
- [x] 所有 `/api/v1` HTTP 路由默认校验 `X-Local-Token`
- [x] `/events` WebSocket 默认校验 query 参数 `token`
- [x] 支持 `allowed_origins`，并校验 Origin
- [x] 响应包含 CSP、`X-Content-Type-Options`、`Referrer-Policy`
- [x] 关闭 Swagger/ReDoc，仅保留 `/api/v1/openapi.json`
- [x] 补充错误码和测试：无 token、错误 token、正确 token、错误 Origin、WS 错误 token

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_api.py
```

### 2. 完整双模式启动

目标文件：根目录 `main.py`、`backend/devbase/desktop/launcher.py`。

- [x] 默认启动桌面模式
- [x] `--browser` 浏览器模式
- [x] `--browser --reload` 支持调试重载
- [x] `--no-browser` 不自动打开浏览器
- [x] `--host`、`--port` 和 `PLATFORM_HOST`、`PLATFORM_PORT`
- [x] 启动前检查 `web/dist/index.html`
- [x] 服务返回健康状态后再打开桌面窗口或浏览器
- [x] 保留 pywebview/WebView2 桌面入口

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_launcher.py
```

### 3. 领域端口契约

目标文件：`backend/devbase/domain/ports.py`。

- [x] 保留 `ProgressSink`：进度上报 + 取消检查
- [x] 端口使用 `@runtime_checkable Protocol`
- [x] 增加必要的扩展端口（只增加已有业务确实需要的端口）
- [x] domain 不依赖 FastAPI、线程实现或桌面框架
- [x] 补充 Protocol 运行时检查测试

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_manifest.py
```

### 4. 运行时和状态机统一

目标文件：`backend/devbase/application/job_runtime.py`、`backend/devbase/domain/job.py`。

- [x] 统一名称为 `JobRuntime`
- [x] `JobStatus` 支持 `QUEUED`、`RUNNING`、`CANCELLING`、`SUCCEEDED`、`COMPLETED_WITH_WARNINGS`、`CANCELLED`、`FAILED`
- [x] 增加通用 `JobPhase` 和 `JobTrigger`
- [x] 所有终态正确实现 `is_terminal`
- [x] 保留单活跃任务约束和窗口生命周期接口
- [x] 不将发票专用阶段逻辑写入基础运行时

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_runtime.py tests/test_api.py
```

### 5. 资源提供者

目标文件：`backend/devbase/domain/resources.py`。

- [x] `ResourceProvider` Protocol
- [x] `InMemoryResourceProvider` 和默认单例
- [x] 未知 key 返回 key
- [x] 缺少格式参数时返回原模板
- [x] 基础表只放通用任务状态文本，不放发票业务文案

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_manifest.py
```

### 6. 事件总线融合

目标文件：`backend/devbase/application/event_bus.py`、`domain/events.py`、API WebSocket 路由。

- [x] 有界订阅队列
- [x] 关键事件不丢失
- [x] progress 只保留最新值，避免慢消费者堆积
- [x] 阻塞读取、超时和优雅关闭
- [x] 保留 `RuntimeSnapshot` 和 event cursor
- [x] WebSocket 重连：快照后从 cursor 继续推送
- [x] 验证断线、重连、慢消费者、取消和关闭场景

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_api.py tests/test_event_bus.py
```

如果不存在 `tests/test_event_bus.py`，先补测试文件，再执行命令。

### 7. 通用日志配置

新增：根目录或后端包内的 `logger_config.py`，位置与最终包导入方式保持一致。

- [x] `setup_logging(log_name="app.log")`
- [x] PyInstaller 开发/冻结模式路径一致
- [x] `logs/` 自动创建
- [x] `RotatingFileHandler`：1 MB、5 个备份
- [x] 重复调用不重复添加 handler

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_logger_config.py
```

如果不存在该测试，先补充测试。

## P1：架构扩展能力

### 8. Task 与 ToolRegistry

目标文件：`backend/devbase/application/task.py`、`manifest.py`、`job_runtime.py`、API `/tools`。

- [x] `Task`、`TaskContext`、`TaskNotFoundError`
- [x] `ToolDescriptor`：kind、title、group、glyph、access_key、supports_input、mode、task
- [x] registry 注册、查找、排序和重复注册保护
- [x] `POST /jobs/start` 按 kind 启动任务
- [x] `GET /tools` 返回清单
- [x] 支持通用 pipeline 扩展：基础仓库只提供机制，不注册发票任务
- [x] 前端导航从工具清单生成，不硬编码业务工具

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_manifest.py tests/test_runtime.py tests/test_api.py
```

### 9. 窗口生命周期

目标文件：`backend/devbase/application/lifecycle.py`、desktop launcher。

- [x] `LifecyclePolicy` 配置关闭模式
- [x] 关闭窗口时按策略取消、等待或退出
- [x] 正在运行任务和终态任务分别验证
- [x] 与 `JobRuntime.cancel_current()` 行为一致

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_lifecycle.py tests/test_launcher.py
```

### 10. 通用配置与 DPAPI

目标文件：`backend/devbase/config_manager.py`、`secret_store.py`、`config.py`。

- [x] INI 首次生成、读取、写入、锁和默认值
- [x] 通用 `get`/`set` 接口，不包含发票 section
- [x] Windows DPAPI 加解密和 `dpapi:` 前缀
- [x] 非 Windows/CI 使用明确标注为非安全的测试降级
- [x] `reload_config()` 热重载
- [x] 提供 `[app]` 模板；业务项目自行添加 section
- [x] 不把真实密钥写入测试、文档或仓库

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_config.py tests/test_secret_store.py
```

### 11. 版本同步工具

目标文件：根目录 `bump_version.py`。

- [x] 同步 `version.py`、`backend/pyproject.toml`、`web/package.json`、lock 文件、`version_info.txt`
- [x] 支持 patch/minor/major
- [x] `--check` 只读检查
- [x] Windows 四元组版本
- [x] 版权年份自动更新
- [x] 所有替换必须确保字段唯一

最窄验证：

```powershell
cd D:\FN\Zy-DevBase
backend\.venv\Scripts\python.exe -m pytest -q backend/tests/test_build.py
backend\.venv\Scripts\python.exe bump_version.py --check
```

## P2：桌面、前端与打包

### 12. 通用 NativeBridge

目标文件：`backend/devbase/desktop/native_bridge.py`。

- [x] `select_directory(title="选择文件夹")`
- [x] `open_directory(path, checker=None)`
- [x] `get_runtime_info()`
- [x] 前端通过 pywebview window 暴露通用方法
- [x] 发票专属文件选择、日志导出等方法不得进入 DevBase
- [x] 补 Windows 和非 Windows 测试替身

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_native_bridge.py
```

### 13. 前端共享组件

目标目录：`web/src/`。

- [x] API client：统一 token 注入、错误处理、健康检查
- [x] WebSocket：token、cursor、重连和断线状态
- [x] 通用 API types
- [x] Sidebar：折叠、拖拽、导航清单
- [x] StatusBar：版本和连接状态
- [x] BottomPanel：通用日志/详情插槽
- [x] UpdateBanner：通用更新状态展示
- [x] store：工作台状态，不包含发票 feature
- [x] 保留 system/light/dark 主题
- [x] `features/` 只提供扩展位置，不放发票页面

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\web
npm run typecheck
npm run build
```

### 14. `.spec` 打包和构建脚本

目标文件：根目录 `devbase.spec`、`scripts/`。

- [x] `.spec` 负责 PyInstaller 打包
- [x] 使用 `--noupx`，符合域控要求
- [x] 主程序和独立更新器均可打包
- [x] `precheck`：纯英文路径、版本一致性、前端构建入口
- [x] `postverify`：exe、内部文件、Windows 版本信息
- [x] 生成 ZIP 和 SHA-256
- [x] 一键构建脚本只编排，不复制业务逻辑

最窄验证：

```powershell
cd D:\FN\Zy-DevBase
python scripts/precheck.py
python -m PyInstaller devbase.spec --noconfirm
python scripts/postverify.py
```

## P3：GitHub Release 自动更新

### 15. 通用更新体系

目标文件：`backend/devbase/application/update_checker.py`、`backend/devbase/desktop/update_*.py`、API、前端 UpdateBanner、SOP。

- [x] 语义化版本比较
- [x] Release 资产按配置规则选择，不写死发票文件名
- [x] 下载临时文件并校验 SHA-256
- [x] ready 文件/环境变量协议
- [x] 独立更新器等待主程序退出
- [x] 替换前备份，失败自动回滚
- [x] 更新后重启并清理临时文件
- [x] API 提供 check/apply/progress，且复用本地 token
- [x] 前端显示检查、下载、应用、失败和回滚状态
- [x] SOP 写明发布、验证、回滚和人工恢复步骤

最窄验证：

```powershell
cd D:\FN\Zy-DevBase\backend
python -m pytest -q tests/test_update_checker.py tests/test_update_helper.py tests/test_update_manager.py
```

## 完成验收

```powershell
cd D:\FN\Zy-DevBase
backend\.venv\Scripts\python.exe -m pytest -q
cd web
npm run typecheck
npm run build
```

然后检查：

- [x] `git diff --check` 无空白错误
- [x] 所有新增通用能力都有测试
- [x] DevBase 中没有发票业务名称、税号、邮箱、AI provider 或发票页面
- [x] README 目录结构、启动方式、API 和扩展说明已同步
- [x] `DEVBASE_UPGRADE_TASKS.md` 的复选框与实际状态一致
- [ ] 仅在全部验证通过后提交和推送

## 发票项目后续适配边界

DevBase 完成后，发票项目再单独适配：

1. 将发票流程注册为项目自己的工具或 pipeline
2. 保留 scan/process/audit/archive 的业务实现，不复制回 DevBase
3. 添加 `[business]`、`[email]`、`[ai]` 配置 section
4. 添加发票专属 NativeBridge 方法
5. 添加发票 Feature 视图
6. 删除已经由 DevBase 提供的通用实现副本

# DevBase 更新 SOP

## 约定

- GitHub 仓库：`SYNTEC-40101720/Zy-DevBase`
- 稳定标签：`vX.Y.Z`
- 主程序：`SYNTEC_DevBase.exe`
- 独立更新器：`SYNTEC_DevBase-updater.exe`
- 资产前缀：`SYNTEC_DevBase-`，资产必须是 ASCII `.zip`
- ZIP 顶层目录：`SYNTEC_DevBase/`
- 用户数据：安装目录中的 `config/` 和 `logs/`

## 发布

1. 在仓库根目录、纯英文路径执行 `bump_version.py patch|minor|major`。
2. 执行 `backend\.venv\Scripts\python.exe scripts\build_release.py`。
3. 确认 `release/SYNTEC_DevBase-X.Y.Z.zip` 和同名 `.sha256` 已生成。
4. 创建稳定 GitHub Release，标签使用 `vX.Y.Z`，不要使用 Draft 或 Pre-release。
5. 上传 ZIP；Release API 的资产名、下载 URL 和 SHA-256 digest 必须与清单匹配。
6. 用 `gh release view vX.Y.Z --repo SYNTEC-40101720/Zy-DevBase --json tagName,isDraft,isPrerelease,assets` 复核上传结果。

## 客户端流程

1. `/api/v1/updates/check` 只查询固定 GitHub 仓库的最新稳定 Release，并用数字版本比较。
2. `/api/v1/updates/apply` 仅执行下载、SHA-256 校验、安全解压并生成 `ready.json`，适用于浏览器/Agent 调试或手工分步流程。
3. 桌面模式使用 `/api/v1/updates/apply-and-restart`：先验证 bundled updater 存在，再执行 stage；将当前主进程 PID 原子写入 `ready.json`，启动 `SYNTEC_DevBase-updater.exe --ready-file <path>`，响应发送后关闭桌面窗口并停止 API 进程。
4. 独立 updater 读取 `ready.json`，轮询等待 PID 退出（30 秒上限）后，将 staging 移到原安装路径，恢复 `config/`、`logs/`，启动新主程序。
5. 替换或数据恢复失败时，删除不完整的新目录并恢复 backup；成功后删除 backup、ready 文件和临时下载目录。
6. `PLATFORM_UPDATE_TIMEOUT` 可覆盖下载 socket 超时（默认 60 秒，最小 5 秒）；`PLATFORM_UPDATE_MAX_BYTES` 可覆盖资产大小上限（默认 512 MiB，最小 1 MiB）。

## 验收

- 当前版本低于、等于、高于 Release 分别验证。
- 验证错误仓库 URL、非 HTTPS URL、错误前缀、多个 ZIP、空文件、超大文件和 SHA-256 不匹配均拒绝。
- 验证 ZIP 路径穿越、绝对路径、符号链接和多顶层目录均拒绝。
- 验证运行中主进程、安装目录不可写、替换失败后的回滚。
- 验证 `config/`、`logs/` 内容在成功更新和回滚后保留。
- 在干净 Windows 环境执行至少一次真实替换冒烟；本地单元测试不能替代该步骤。

## 人工恢复

如果 updater 报告回滚失败，不要删除现场。保留 `.failed`、`.backup-*`、ready 文件和日志，记录当前安装路径与 SHA-256。优先将完整 backup 目录恢复为安装目录，确认主程序版本资源和用户数据后再清理临时目录。

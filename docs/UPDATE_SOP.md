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
2. `/api/v1/updates/apply` 下载到临时目录，校验 SHA-256，安全解压并生成 `ready.json`。
3. 独立 updater 从临时目录启动，等待主进程退出，再把旧安装目录移动到同卷 backup。
4. updater 将 staging 移到原安装路径，恢复 `config/`、`logs/`，启动新主程序。
5. 替换或数据恢复失败时，删除不完整的新目录并恢复 backup；成功后删除 backup、ready 文件和临时下载目录。

## 验收

- 当前版本低于、等于、高于 Release 分别验证。
- 验证错误仓库 URL、非 HTTPS URL、错误前缀、多个 ZIP、空文件、超大文件和 SHA-256 不匹配均拒绝。
- 验证 ZIP 路径穿越、绝对路径、符号链接和多顶层目录均拒绝。
- 验证运行中主进程、安装目录不可写、替换失败后的回滚。
- 验证 `config/`、`logs/` 内容在成功更新和回滚后保留。
- 在干净 Windows 环境执行至少一次真实替换冒烟；本地单元测试不能替代该步骤。

## 人工恢复

如果 updater 报告回滚失败，不要删除现场。保留 `.failed`、`.backup-*`、ready 文件和日志，记录当前安装路径与 SHA-256。优先将完整 backup 目录恢复为安装目录，确认主程序版本资源和用户数据后再清理临时目录。

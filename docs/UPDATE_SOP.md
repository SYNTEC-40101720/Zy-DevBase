# DevBase 更新 SOP

## 约定

- GitHub 仓库：`SYNTEC-40101720/Zy-DevBase`
- 稳定标签：`vX.Y.Z`
- 主程序：`SYNTEC_DevBase.exe`（不再包含独立更新器）
- 资产前缀：`SYNTEC_DevBase-`，发布资产使用 ASCII `.zip`
- ZIP 顶层目录：`SYNTEC_DevBase/`
- 用户数据：安装目录中的 `config/` 和 `logs/`，人工升级时保留

## 客户端：只检查、只提示

GitHub 在本地网络中访问不稳定，小工具不应承担下载、安装、回滚和自重启的完整更新系统。

1. 启动、打开工作台或设置页均不访问 GitHub；不轮询、不后台重试。
2. 用户点击设置页「检查更新」，才调用带本地令牌保护的 `GET /api/v1/updates/check`。
3. 后端只读取固定仓库的最新稳定 Release 元数据，按数字比较版本；不要求 ZIP、大小或 SHA-256 字段存在。
4. 发现新版本时显示版本号和「打开发布页」。仅在用户点击链接后由浏览器打开固定仓库的 HTTPS 发布页，下载、解压和替换由用户自行操作。
5. 当前版本等于或高于 Release 时显示「当前无需更新」，不提示降级。
6. 断网、超时、限流、私有仓库无权访问、无 Release 或元数据错误时显示「检查未完成」，不能误报「已是最新」。本地任务和页面不受影响。
7. 默认请求 socket 超时为 5 秒，`PLATFORM_UPDATE_TIMEOUT` 可设置有限的 1–30 秒；非法值回退到 5 秒。该值是网络操作超时，不承诺整个检查在精确秒数内结束（DNS 等受系统影响）。

响应字段为 `current`、`latest`、`available`、`release_url`、`error`。旧的 `/updates/apply`、`/updates/apply-and-restart`、`/updates/progress` 和安装进度契约已移除。

`PLATFORM_INSTALL_DIR`、`PLATFORM_UPDATE_DIR`、`PLATFORM_UPDATE_MAX_BYTES` 不再参与更新检查。客户端不会扫描、删除或清理旧版本遗留的临时更新目录。

> 默认采用匿名 GitHub API 请求；私有仓库无匿名访问权限时检查会显示未完成。不要把 GitHub token 嵌进分发给用户的工具；仍可直接用浏览器或内部渠道领取安装包。

## 发布

1. 在仓库根目录、纯英文路径执行 `bump_version.py patch|minor|major`（只检查时使用 `--check`）。
2. 执行测试与前端检查：后端 `python -m pytest`，前端 `npm run typecheck`、`npm test`。
3. 执行 `backend\.venv\Scripts\python.exe scripts\build_release.py`；先构建前端，再预检、打包主程序并校验版本资源，不再构建或合并 updater。
4. 确认 `release/SYNTEC_DevBase-X.Y.Z.zip` 和同名 `.sha256` 已生成。
5. 创建稳定 GitHub Release，标签使用 `vX.Y.Z`，不要使用 Draft 或 Pre-release。
6. 上传 ZIP；用 `gh release view vX.Y.Z --repo SYNTEC-40101720/Zy-DevBase --json tagName,isDraft,isPrerelease,assets` 核对资产名、大小与 SHA-256。发布侧仍保留摘要校验，与客户端不下载并不矛盾。

## 人工升级

1. 退出应用，备份旧安装目录以及 `config/`、`logs/` 和派生项目自己的业务数据。
2. 从发布页或内部渠道取得 ZIP，按发布方提供的 SHA-256 校验，解压到新的纯英文路径。
3. 将需保留的用户数据复制到新目录，启动新程序并核对版本与功能。
4. 若新版本异常，退出后使用保留的旧目录恢复。工具本身不会自动替换安装目录或回滚。

## 验收

- 离线启动和本地任务运行无需 GitHub；设置页未点击前没有检查请求。
- 当前版本低于、等于、高于 Release 的比较正确。
- 无 ZIP/无 digest 时仍能提示有效的稳定版本。
- 发布页 URL 必须与固定仓库、HTTPS 和 tag 完全匹配，拒绝跨站/跨仓库/不匹配版本的链接。
- 超时、无 Release、限流、非法 JSON 与 draft/prerelease 均返回未完成，不自动重试。
- 设置页直接显示结果，检查中按钮禁用；提示链接不执行安装或重启。
- 后端 OpenAPI 不再暴露更新写操作；打包编排只构建主程序。

## 发布记录

### v0.3.8（2026-10-16）

- Release: [v0.3.8](https://github.com/SYNTEC-40101720/Zy-DevBase/releases/tag/v0.3.8)
- 资产：`SYNTEC_DevBase-0.3.8.zip`（20,731,021 bytes）
- SHA-256：`4cf317c68da0df284574baed6806d081425efef1a4598e8fbc5e82d228a95700`（本地 sidecar 与 GitHub digest 一致）
- 改动：仅手动检查并打开 Release 页面；删除下载、stage、replace、rollback、restart 与独立 updater。
- 验证：后端 153 passed（1 条 Starlette 弃用警告）；前端 typecheck、7 Vitest、Vite build 全绿；版本一致性与打包 precheck 全绿；GitHub Actions Python 3.12/3.13、前端、版本检查全绿；PyInstaller build 与 `postverify` 通过。
- 打包行为冒烟：冻结程序以 browser/no-browser 模式启动，API 返回 v0.3.8，鉴权和只读路由正确；新版本链接、离线错误、无需更新三种 UI 状态及本地导航均通过，未见 JS 错误。模拟新版本/断网 API 响应使用本地拦截。
- 限制：**实际 WebView2 桌面窗口关闭后 exit 0 / 端口释放的验收未通过，不能据此宣称干净退出已验证。** 本次关闭检查未能可靠操作/确认原生窗口；桌面应用生命周期本身未改。需在有交互式桌面的目标机补做人工关闭验收；这不影响本版下载提示功能及 CI 结果。

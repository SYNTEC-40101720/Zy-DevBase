# DevBase 路线图

模板能力的演进计划。每项含触发条件——不满足触发条件就不做，保持模板精简。

## 当前状态（v0.3.7）

- 后端分层骨架（domain / application / api / desktop）稳定，148 个测试全绿
- 桌面壳 + 独立 updater（staging / backup / 回滚）完整
- 发布链路（bump_version / precheck / build_release / postverify）完整
- CI：GitHub Actions 跑后端 pytest（3.12/3.13）+ 前端 typecheck/test/build + 版本一致性检查
- 待办：第一个真实派生项目尚未产生反馈回填

## 已评估、暂不做

### 任务持久化（SQLite/JSON 落盘）

**结论：等第一个派生项目提出需求再做。**

- 当前边界"任务状态进程重启即丢"对模板本身够用——演示任务只验证运行时契约
- 桌面工具的任务历史需求形态各异（审计日志？断点续跑？仅展示?），先做大概率返工
- 若做：在 `application` 层加 `JobStore` 端口（对齐 `ProgressSink` 的端口模式），内存实现为默认，SQLite 实现为可选依赖，不破坏现有测试

**触发条件**：某派生项目需要跨会话任务记录，且第二个项目也需要同样的形态。

### 多任务并发运行时

**结论：等批量处理类工具真实出现再做。**

- 单任务模型让"取消/冲突检测/事件重放"都简单可靠；多任务会牵动事件总线、
  WebSocket 快照结构（当前以"当前任务"为权威）、前端 BottomPanel 事件流
- 若做：`_active: _MutableJob` → 任务表 + 每任务取消事件，API 层增 `job_id` 路径参数；
  `/jobs/current` 保留为兼容别名

**触发条件**：某派生项目需要同时跑 ≥2 个后台任务（而非排队串行即可满足）。

## 近期事项

| 事项 | 状态 |
| --- | --- |
| NEW_PROJECT_SOP 补"清理演示内容"章节 | ✅ v0.3.7 后完成 |
| CI workflow（pytest 矩阵 + 前端 + 版本一致性） | ✅ v0.3.7 后完成 |
| 本地 release zip 清理（GitHub 资产已核验） | 待用户确认执行 |
| 第一个真实派生项目 + SOP 回填 | ⬜ 下一步 |
| 依赖升级评估（Vite 6 / React 19 / TS 5.7 有安全补丁时） | ⬜ 按需 |

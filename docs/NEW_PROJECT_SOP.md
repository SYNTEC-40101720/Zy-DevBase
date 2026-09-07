# 新建项目 SOP

从 DevBase 模板派生一个新项目并改名的完整流程。复制模板后照此执行，把 `devbase` / `DevBase` 系列标识替换成新项目名。

本文以 `modbus` 为示例目标名，实际使用时换成自己的项目名。

## 0. 前置：复制模板

```bash
# 在目标空仓库目录里，从模板导出 git 追踪文件（不含 build/dist/node_modules/.venv 等产物）
cd /d/FN/<新项目>
git archive --format=tar HEAD | tar -x -C .
```

> 用 `git archive` 而非整目录复制，可避免带入 `.venv`、`node_modules`、`dist`、`build`、`release`、`logs`、`.pytest_cache`、`.vscode`、`.claude` 等本地/产物目录。模板的 `.gitignore` 已排除这些，但整目录复制仍会带过来。

## 1. 替换映射

按 **最长匹配优先** 顺序做全局文本替换，避免短串误伤长串（例如 `devbase` 不应先替换，否则 `Zy-DevBase` 会变成 `Zy-Modbus` 而非预期的 `Modbus`）。

| 旧值 | 新值 | 说明 |
|---|---|---|
| `Zy-DevBase` | `<新仓名>` | GitHub 仓名，例如 `Modbus` |
| `SYNTEC_DevBase` | `SYNTEC_<新名>` | 可执行文件 / bundle 名（下划线） |
| `SYNTEC-DevBase` | `SYNTEC-<新名>` | 版本信息字符串（连字符） |
| `DevBase` | `<新名>` | 显示名、窗口标题、README 标题 |
| `DEVBASE` | `<新名大写>` | 前端全局变量，如 `__DEVBASE_TOKEN__` → `__MODBUS_TOKEN__` |
| `devbase` | `<新名小写>` | Python 包名、import、spec、配置路径 |

仓名（`Zy-DevBase` → `Modbus`）按实际 GitHub 仓库定，通常与远程仓库名一致。

## 2. 目录与文件重命名

文本替换之外，还要重命名带 `devbase` 字样的目录和文件：

```bash
git mv backend/devbase backend/<新名小写>
git mv devbase.spec <新名小写>.spec
git mv devbase_updater.spec <新名小写>_updater.spec
```

## 3. 批量替换脚本

以下脚本对仓库内所有文本文件（跳过二进制和产物目录）按上表顺序替换。把它存成临时脚本运行，或直接在 shell 里执行：

```python
import os

subs = [
    ('Zy-DevBase', 'Modbus'),          # 换成你的仓名
    ('SYNTEC_DevBase', 'SYNTEC_Modbus'),
    ('SYNTEC-DevBase', 'SYNTEC-Modbus'),
    ('DevBase', 'Modbus'),
    ('DEVBASE', 'MODBUS'),
    ('devbase', 'modbus'),
]

skip_dirs = {'.git', 'node_modules', '.venv', '__pycache__',
             '.pytest_cache', 'dist', 'build', 'release'}

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in skip_dirs]
    for f in files:
        p = os.path.join(root, f)
        with open(p, 'rb') as fh:
            raw = fh.read()
        if b'\x00' in raw:          # 跳过二进制
            continue
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            continue
        new = text
        for a, b in subs:
            new = new.replace(a, b)
        if new != text:
            with open(p, 'w', encoding='utf-8', newline='') as fh:
                fh.write(new)
```

## 4. 验证

```bash
# 4.1 确认无残留引用
git grep -niE "devbase" -- . ':(exclude).git'   # 应输出 (none)

# 4.2 建临时 venv 跑后端测试
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[test]"
.venv/Scripts/python -m pytest
cd ..
rm -rf backend/.venv

# 4.3 确认包能导入
cd backend && python -c "import sys; sys.path.insert(0,'.'); import <新名小写>; print('OK')" && cd ..
```

**预期结果：**
- `git grep` 无输出。
- pytest 全绿，**除 `test_packaging_precheck_passes` 外**——该测试要求 `web/dist/index.html` 存在（前端构建产物），模板默认不带 `dist/`。跑一次 `cd web && npm install && npm run build` 后即通过，与改名无关。

## 5. 提交

```bash
git add -A
git commit -m "chore: 引入 DevBase 开发基础模板"
git commit -m "refactor: 将 devbase 重命名为 <新名小写>"   # 若改名单独提交
git push origin main
```

## 6. 常见坑

- **替换顺序**：必须先替换长串（`Zy-DevBase`、`SYNTEC_DevBase`）再替换短串（`devbase`），否则 `Zy-DevBase` 会被先拆成 `Zy-Modbus`。
- **仓名 vs 包名**：`Zy-DevBase` 是 GitHub 仓名（→ `Modbus`），`devbase` 是 Python 包名（→ `modbus`），两者替换目标不同，不要混用。
- **`package-lock.json` 会被改**：里面只有 npm 包名 `devbase-web` 两处，随 `package.json` 一起被替换是正确的，无需手动回滚。
- **前端全局变量**：`__DEVBASE_TOKEN__` / `__DEVBASE_API_BASE__` 在 `web/src/api/client.ts`，由后端 `desktop/launcher.py` 注入到 window 对象——两端必须同时替换（脚本会一并处理），否则 token 注入失效。
- **`bump_version.py` 里有硬编码路径**：`backend/devbase/__init__.py` 和 `backend/devbase/api/app.py`，改名后这两处路径也要同步（脚本会替换），否则版本号同步报错。
- **不要改 `version.py` / `version_info.txt` 里的版本号**：那是版本内容，不是项目名；脚本只改其中的 `SYNTEC_DevBase` 等标识，不动 `0.3.7` 这类版本数字。

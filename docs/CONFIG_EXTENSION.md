# 配置管理扩展指南

> Issue #9 验收项：派生项目追加业务 section 文档说明

## 概述

DevBase 的 `ConfigManager` 使用 INI 配置文件，默认模板只包含 `[app]` section。
派生项目需要追加业务 section（如 `[invoice]`、`[ai_audit]`），应遵循以下扩展模式。

---

## 默认模板

DevBase 的 `DEFAULT_CONFIG` 只包含业务无关的基础 section：

```ini
[app]
name = DevBase
config_version = 1
```

`config.py` 中的 `DEFAULT_CONFIG` 是唯一模板来源：

```python
DEFAULT_CONFIG: dict[str, dict[str, str]] = {
    "app": {
        "name": "DevBase",
        "config_version": "1",
    }
}
```

---

## 扩展模式

### 原则

1. **不修改 DevBase 的 `DEFAULT_CONFIG`** — 派生项目创建自己的
   配置默认值 dict
2. **注入到 `ConfigManager`** — 通过构造函数 `defaults=` 参数注入
3. **首次生成模板** — `ConfigManager.reload_config()` 首次读取时会
   合并默认值和磁盘内容
4. **热重载** — 用户在 Web 设置中修改配置后，调用 `reload_config()`
   立即生效，无需重启

### 方式一：注入业务默认值（推荐）

```python
from devbase.config_manager import ConfigManager
from devbase.config import default_values

# 1. 定义业务默认值
INVOICE_DEFAULTS = {
    "app": {
        "name": "InvoiceProcessor",
        "config_version": "1",
    },
    "invoice": {
        "inbox_dir": "",
        "output_dir": "",
        "tax_number": "",
        "auto_archive": "true",
        "retry_limit": "3",
    },
    "ai_audit": {
        "api_endpoint": "",
        "api_key_ref": "dpapi:encrypted_key",
        "timeout_seconds": "30",
    },
}

# 2. 创建 ConfigManager 时注入
config_manager = ConfigManager(
    path="~/.devbase/config.ini",
    defaults=INVOICE_DEFAULTS,
)

# 3. 读取业务字段
tax_number = config_manager.get("invoice", "tax_number", fallback="")
inbox_dir = config_manager.get("invoice", "inbox_dir", fallback="")

# 4. 写入业务字段
config_manager.set("invoice", "tax_number", "440301123456789")
config_manager.save()
```

生成的 `config.ini` 模板：

```ini
[app]
name = InvoiceProcessor
config_version = 1

[invoice]
inbox_dir =
output_dir =
tax_number =
auto_archive = true
retry_limit = 3

[ai_audit]
api_endpoint =
api_key_ref = dpapi:encrypted_key
timeout_seconds = 30
```

### 方式二：动态扩展 defaults dict

派生项目可在运行时动态追加 section：

```python
from devbase.config import default_values, DEFAULT_CONFIG

def get_invoice_defaults() -> dict[str, dict[str, str]]:
    """返回含业务 section 的默认值。"""
    defaults = default_values()  # 深拷贝 DevBase 默认值
    defaults["invoice"] = {
        "inbox_dir": "",
        "output_dir": "",
        "tax_number": "",
    }
    return defaults
```

---

## 与热重载配合

用户在 Web 设置页面修改配置后，调用 `reload_config()` 使改动立即生效：

```python
from devbase.config_manager import ConfigManager

config_manager = ConfigManager(
    path="~/.devbase/config.ini",
    defaults=INVOICE_DEFAULTS,
)

# 用户在 Web 修改了 tax_number，保存到磁盘后：
config_manager.reload_config()

# 立即可读到新值
new_tax = config_manager.get("invoice", "tax_number", fallback="")
```

---

## 与 DPAPI 密钥存储配合

业务 section 中的敏感字段（如 API Key）不应明文存储，应使用
`secret_store` 加密：

```python
from devbase.secret_store import encrypt, decrypt

# 配置文件中只存加密后的值
config_manager.set("ai_audit", "api_key_ref", f"dpapi:{encrypt(raw_key)}")

# 读取时解密
encrypted_ref = config_manager.get("ai_audit", "api_key_ref", fallback="")
if encrypted_ref and encrypted_ref.startswith("dpapi:"):
    raw_key = decrypt(encrypted_ref.removeprefix("dpapi:"))
```

非 Windows 环境会自动降级为 base64（仅开发用，不安全）。

---

## 注意事项

- **避免硬编码**：不要在代码里写死税号、路径等业务参数，统一走
  `ConfigManager` 读写
- **线程安全**：`ConfigManager` 使用 RLock + 文件锁，多线程读写安全
- **文件锁超时**：默认 5 秒，可通过 `lock_timeout` 参数调整
- **首次生成模板**：`ConfigManager.__init__()` 调用 `reload_config()`
  会在文件不存在时生成包含默认值的模板文件
- **不要在同步代码中直接调用网络操作**：热重载后生效是同步的，但
  如配置涉及重连网络客户端，应在应用层异步处理

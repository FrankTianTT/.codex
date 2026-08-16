"""
API 密钥管理 — keyring 模式模板
===================================
所有调用外部 API 的 Python 脚本必须遵循此模式。
密钥优先级：keyring（系统钥匙链）→ 环境变量 → 报错引导设置。

使用方法：
    uv run --with keyring python3 <脚本>

创建新技能需要 API 密钥时：
    1. 复制此文件中的 `_get_api_key()` 函数到你的脚本
    2. 运行前引导用户通过 getpass 交互式存储密钥（无回显，无 shell 历史泄露）：
       ```
       uv run --with keyring python3 -c "
       import keyring, getpass
       key = getpass.getpass('粘贴 YOUR_API_KEY: ')
       keyring.set_password('service-name', '$USER', key)
       print('✅ done')
       "
       ```
    3. 绝对不要亲自在 shell 命令中输入用户的密钥——始终让 getpass 以交互方式处理
"""

import os

try:
    import keyring
except ImportError:
    keyring = None


def _get_api_key(service: str, env_var: str) -> str:
    """读取 API key，优先级：keyring → 环境变量 → 报错引导设置。"""
    if keyring:
        val = keyring.get_password(service, os.environ.get("USER", "default"))
        if val:
            return val

    val = os.environ.get(env_var)
    if val:
        return val

    raise SystemExit(
        f"❌ 未找到 {service} 的 API key。请设置：\n\n"
        f"   uv run --with keyring python3 -c \"\n"
        f"import keyring, getpass\n"
        f"key = getpass.getpass('粘贴 {env_var}: ')\n"
        f"keyring.set_password('{service}', '$USER', key)\n"
        f"print('✅ 已存入系统钥匙链')\"\n\n"
        f"  或：export {env_var}='<your-key>'\n"
    )

#!/usr/bin/env python3
"""vision-tools 共享工具函数 —— 避免各脚本重复实现相同逻辑。

所有脚本通过 `from _shared import get_api_key, encode_image` 引入。
"""

import base64, os

try:
    import keyring as _keyring
except ImportError:
    _keyring = None


def get_api_key(service: str, env_var: str) -> str:
    """读取 API key，优先级: keyring → 环境变量 → 报错引导设置。

    Args:
        service: keyring 服务名（如 'zhipu-api-key'）
        env_var: 环境变量名（如 'ZHIPU_API_KEY'）
    """
    # 1. keyring（跨平台加密钥匙链，macOS Keychain）
    if _keyring:
        val = _keyring.get_password(service, os.environ.get("USER", "default"))
        if val:
            return val
    # 2. 环境变量（降级方案）
    val = os.environ.get(env_var)
    if val:
        return val
    # 3. 都没有 → 报错并引导设置
    raise SystemExit(
        f"❌ 未找到 {service} 的 API key。请选择一种方式设置：\n\n"
        f"   方式一（推荐，加密存储）:\n"
        f"     uv run --with keyring python3 -c \"\n"
        f"import keyring, getpass\n"
        f"key = getpass.getpass('粘贴 {env_var}: ')\n"
        f"keyring.set_password('{service}', '{os.environ.get('USER', 'default')}', key)\n"
        f"print('✅ 已存入系统钥匙链')\"\n\n"
        f"   方式二（临时使用）:\n"
        f"     export {env_var}='<your-key>'\n"
    )


def encode_image(path: str) -> tuple[str, str]:
    """将图片文件编码为 base64，返回 (base64_string, mime_type)。"""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(path)[1].lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext, "image/png")
    return b64, mime

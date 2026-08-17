#!/usr/bin/env python3
"""vision-tools 共享工具函数 —— 避免各脚本重复实现相同逻辑。

所有脚本通过 `from _shared import get_api_key, encode_image` 引入。
"""

import base64
import os

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
    # 3. 都没有 → 抛出普通异常，让调用方可以尝试下一个已配置服务
    raise RuntimeError(
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
    if not os.path.isfile(path):
        raise ValueError(f"图片不存在: {path}")
    size = os.path.getsize(path)
    if size <= 0 or size > 20 * 1024 * 1024:
        raise ValueError(f"图片大小必须在 1B 到 20MB 之间: {size}B")

    ext = os.path.splitext(path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    if ext not in mime_map:
        raise ValueError(f"不支持的图片格式: {ext}")

    with open(path, "rb") as f:
        data = f.read()
    valid_magic = (
        (ext == ".png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
        or (ext in {".jpg", ".jpeg"} and data.startswith(b"\xff\xd8\xff"))
        or (ext == ".webp" and data.startswith(b"RIFF") and data[8:12] == b"WEBP")
    )
    if not valid_magic:
        raise ValueError(f"扩展名与图片内容不一致: {path}")
    return base64.b64encode(data).decode(), mime_map[ext]

#!/usr/bin/env python3
"""图片结构化提取 —— 将图片转为可直接渲染的 LaTeX / Pseudocode / Markdown。

用法:
  uv run --with keyring python3 extract.py --mode formula image.jpg
  uv run --with keyring python3 extract.py --mode algorithm image.jpg
  uv run --with keyring python3 extract.py --mode table image.jpg

输出可直接用于 Obsidian 渲染:
  - formula → $$...$$ LaTeX 公式
  - algorithm → PascalCase 伪代码（兼容 obsidian-pseudocode 插件）
  - table → Markdown 表格
"""

import json, os, sys, time, urllib.request, urllib.error
from _shared import get_api_key, encode_image

ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MINIMAX_URL = "https://api.minimaxi.com/v1/chat/completions"

MODES = {
    "formula": {
        "label": "📐 公式提取",
        "prompt": (
            "You are a LaTeX expert. The image contains mathematical formulas, theorems, and equations. "
            "Your ONLY task: output the EXACT LaTeX code for ALL mathematical content visible in this image. "
            "Use $$...$$ for display equations, $...$ for inline math. "
            "Preserve ALL mathematical symbols, Greek letters, subscripts, superscripts, fractions, integrals, sums exactly as they appear. "
            "Include theorem statements, proof steps, and any mathematical notation. "
            "Keep ALL original language in \\text{} blocks — do NOT translate Chinese to English. "
            "Output ONLY the LaTeX code. NO explanations. NO descriptions. NO markdown wrappers. "
            "Start directly with the LaTeX code."
        ),
    },
    "algorithm": {
        "label": "📝 算法提取",
        "prompt": (
            "You are an algorithmic pseudocode expert. The image contains an algorithm written in pseudocode. "
            "Your ONLY task: convert this algorithm into PascalCase pseudocode format compatible with pseudocode.js "
            "(used by the obsidian-pseudocode Obsidian plugin). "
            "Use these EXACT PascalCase commands: "
            "\\Require{...}, \\Ensure{...}, \\State, \\For{cond}, \\EndFor, "
            "\\While{cond}, \\EndWhile, \\If{cond}, \\ElsIf{cond}, \\Else, \\EndIf, \\Comment{...}, \\Return{...}. "
            "Wrap in \\begin{algorithmic} ... \\end{algorithmic}. "
            "Do NOT use UPPERCASE (\\FOR, \\IF, \\WHILE, \\STATE etc.) — pseudocode.js does not recognize them. "
            "Preserve ALL variable names, mathematical notation, and comments exactly as they appear. "
            "Keep ALL original language — do NOT translate Chinese to English. "
            "Output ONLY the pseudocode. NO explanations. NO descriptions. NO markdown wrappers."
        ),
    },
    "table": {
        "label": "📊 表格提取",
        "prompt": (
            "You are a Markdown table expert. The image contains a table or structured comparison. "
            "Your ONLY task: convert the table into a Markdown table format with pipes | for columns. "
            "Use $...$ for any inline math formulas within cells. "
            "Keep ALL original language — do NOT translate. "
            "Preserve ALL rows, columns, and cell contents exactly. "
            "Output ONLY the Markdown table. NO explanations. NO descriptions. NO extra text."
        ),
    },
}


def _build_content(image_path: str, mode: str) -> list:
    """构建 vision API 请求 content 列表"""
    mode_config = MODES[mode]
    b64, mime = encode_image(image_path)
    return [
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        {"type": "text", "text": mode_config["prompt"]},
    ]


def call_zhipu(image_path: str, mode: str) -> dict:
    """智谱 GLM-4.6V"""
    content = _build_content(image_path, mode)
    body = {
        "model": "glm-4.6v",
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096,
        "temperature": 0.1,
    }
    api_key = get_api_key("zhipu-api-key", "ZHIPU_API_KEY")
    t0 = time.time()
    req = urllib.request.Request(
        ZHIPU_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read())
    return {
        "ok": True,
        "model": "zhipu/glm-4.6v",
        "elapsed": time.time() - t0,
        "text": result["choices"][0]["message"]["content"],
    }


def call_minimax(image_path: str, mode: str) -> dict:
    """MiniMax-M3 备选"""
    content = _build_content(image_path, mode)
    body = {
        "model": "MiniMax-M3",
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096,
        "temperature": 0.1,
        "thinking": {"type": "disabled"},
    }
    api_key = get_api_key("minimax-api-key", "MINIMAX_API_KEY")
    t0 = time.time()
    req = urllib.request.Request(
        MINIMAX_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read())
    content_text = result["choices"][0]["message"].get("content", "")
    # 去掉 <think>...</think> 标签
    if "<think>" in content_text and "</think>" in content_text:
        end_think = content_text.index("</think>") + len("</think>")
        content_text = content_text[end_think:].strip()
    return {
        "ok": True,
        "model": "minimax/MiniMax-M3",
        "elapsed": time.time() - t0,
        "text": content_text,
    }


def extract(image_path: str, mode: str) -> dict:
    """提取结构化内容，优先智谱 glm-4.6v，失败降级到 MiniMax-M3"""
    # 主力: 智谱
    try:
        return call_zhipu(image_path, mode)
    except Exception as e:
        print(f"  ⚠️ zhipu/glm-4.6v 失败: {str(e)[:120]}")

    # 降级: MiniMax
    try:
        return call_minimax(image_path, mode)
    except Exception as e:
        return {"ok": False, "error": str(e), "elapsed": 0}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="图片结构化提取")
    parser.add_argument("image", help="图片路径")
    parser.add_argument("--mode", "-m", choices=list(MODES.keys()), required=True,
                       help="提取模式: formula/algorithm/table")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        print(f"❌ 文件不存在: {args.image}")
        sys.exit(1)

    config = MODES[args.mode]
    print(f"{config['label']} | 📷 {os.path.basename(args.image)} ({os.path.getsize(args.image)//1024}KB)")
    print("-" * 60)

    result = extract(args.image, args.mode)
    if result["ok"]:
        print(f"⏱ {result['elapsed']:.1f}s | 🌐 {result['model']}")
        print("-" * 60)
        print(result["text"])
    else:
        print(f"❌ 提取失败: {result.get('error')}")
        sys.exit(1)

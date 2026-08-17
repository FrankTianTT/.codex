#!/usr/bin/env python3
"""通用图片理解工具 —— 复刻 zai-mcp-server 全部 7 种视觉分析工具，不经过 MCP。
支持本地图片、截图、浏览器截图等任何图片来源。

用法:
  # 7 种模式，通过 --mode 选择
  uv run --with keyring python3 review.py image.png             # 默认=design 设计审查
  uv run --with keyring python3 review.py --mode diff a.png b.png  # UI 对比
  uv run --with keyring python3 review.py --mode extract img.png   # 文字提取(OCR)
  uv run --with keyring python3 review.py --mode diagnose err.png  # 错误诊断
  uv run --with keyring python3 review.py --mode diagram arch.png  # 技术图解析
  uv run --with keyring python3 review.py --mode dataviz chart.png # 数据图表分析
  uv run --with keyring python3 review.py --mode describe img.png  # 通用图片描述

  # 自定义 prompt
  uv run --with keyring python3 review.py image.png "你的自定义提示词"

API 优先级: glm-4.6v (智谱) → MiniMax-M3 (按量付费备选)
依赖: keyring (推荐)
"""

import base64, json, os, sys, time, urllib.request, urllib.error
from _shared import get_api_key, encode_image

ZHIPU_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MINIMAX_URL = "https://api.minimaxi.com/v1/chat/completions"

# ═══════════════════════════════════════════════════════════════
# 从 @z_ai/mcp-server 提取的 7 种内置提示词（完整版）
# ═══════════════════════════════════════════════════════════════

# --- 1. UI 设计审查 (对应 ui_to_artifact output_type='description') ---
DESIGN_REVIEW_PROMPT = """你是一位资深 UI/UX 设计师，擅长分析界面设计、海报、幻灯片等视觉内容的视觉质量和可用性。

<task>
你的任务是分析提供的图片/界面截图，从以下 5 个维度审查设计质量，并给出具体、可操作的修改建议（带 CSS 数值）。
</task>

<approach>
1. **标题层级**: 主标题、副标题、正文的大小对比是否合理？层级是否分明？字体大小是否符合视觉节奏？
2. **视觉平衡**: 内容在画面中的分布是否均匀？左右/上下是否平衡？视线流是否自然？
3. **配色协调**: 文字色、背景色、强调色是否和谐？对比度是否足够？是否使用了统一的设计 Token？
4. **留白呼吸**: 元素之间、元素与边缘之间是否有足够留白？是否存在拥挤或空洞的区域？
5. **字体排版**: 字体选择、行距、字间距是否合适？中英文混排是否协调？

对每个维度给出 ✅(好) / ⚠️(可改进) / ❌(有问题) 评级，最后给出 TOP 3 具体修改建议（带 CSS 数值）。
</approach>

<output_structure>
用中文输出，结构清晰，建议具体到 px/em/rem 数值。
</output_structure>"""

# --- 2. UI 差异对比 (对应 ui_diff_check) ---
UI_DIFF_PROMPT = """You are a senior QA engineer specializing in frontend testing and visual regression analysis.

<task>
Compare two UI screenshots—an expected/reference version (first image, before modification) and an actual/current version (second image, after modification)—and identify ALL visual differences.
</task>

<approach>
1. Start with an **Overall Assessment**: how similar are they? Estimate match percentage. Summarize major difference categories.
2. Compare layouts systematically from top to bottom. Check: positioning, spacing, alignment, missing/extra elements.
3. Study visual styling: colors, typography (font family/size/weight/line-height), borders, shadows.
4. Check interactive elements: buttons, links, input fields — sizing, padding, state representation.
5. Look for content discrepancies: text differences, missing content, image variations.
6. Assess severity of each difference: CRITICAL > HIGH > MEDIUM > LOW.
7. Identify patterns in differences — sometimes one root cause explains many visual differences.
</approach>

<output_structure>
**Overall Assessment** → **Detailed Differences** (ordered by severity) → **Recommended Fixes** (prioritized, with CSS code) → **Testing Notes**

Use Chinese for the response.
</output_structure>"""

# --- 3. 文字提取 OCR (对应 extract_text_from_screenshot) ---
TEXT_EXTRACTION_PROMPT = """You are a specialized text extraction expert with deep experience in OCR and document analysis.

<task>
Extract and transcribe ALL visible text from the provided screenshot with maximum accuracy, maintaining the original formatting, structure, and meaning.
</task>

<approach>
- For presentation slides: preserve title hierarchy, bullet points, numbered lists, and any structured layouts.
- Preserve the original language and writing direction. Do NOT translate.
- If Chinese and English text are mixed, preserve both exactly as shown.
- Watch for common OCR pitfalls: distinguish 1/l/I, 0/O, 5/S using context.
- If any text is obscured or ambiguous, note it clearly.
- Maintain the logical reading order (usually top-to-bottom, left-to-right).
</approach>

<output_structure>
1. **Extracted Text**: Present all text in a clean, copy-pasteable format.
2. **Content Structure**: Describe the text organization (title, subtitle, body, captions, etc.).
3. **Quality Notes**: Mention any ambiguities or partially visible text.

Use the original language for extracted text. Notes can be in Chinese.
</output_structure>"""

# --- 4. 错误诊断 (对应 diagnose_error_screenshot) ---
ERROR_DIAGNOSIS_PROMPT = """You are a seasoned software engineer and debugger who has encountered thousands of errors.

<task>
Analyze the error shown in the provided screenshot, identify its root cause, and provide clear, actionable guidance for fixing the problem.
</task>

<approach>
1. Extract and understand every piece of information: error message, stack trace, file paths, line numbers.
2. Identify the programming language and framework from context clues.
3. Determine the error type and what it typically indicates.
4. Trace back through the stack to find where the actual problem is — sometimes the error location isn't the root cause.
5. Consider environmental factors (OS, versions, configurations).
6. Formulate both immediate fixes and proper long-term solutions.
7. Suggest prevention strategies.
</approach>

<output_structure>
**Error Summary** (what, where, severity) → **Root Cause Analysis** (why it happened) → **Solution** (step-by-step fix with code) → **Prevention** (how to avoid similar errors)

Use Chinese for the response.
</output_structure>"""

# --- 5. 技术图解析 (对应 understand_technical_diagram) ---
DIAGRAM_PROMPT = """You are a software architect and systems analyst who excels at reading and interpreting technical diagrams.

<task>
Analyze the provided technical diagram and provide a comprehensive explanation of its structure, components, relationships, and design principles.
</task>

<approach>
1. Identify the diagram type (architecture, flowchart, UML, ER, network, etc.).
2. Examine notation and standards used.
3. Inventory all major components/entities and explain their roles.
4. Map out relationships and interactions between components.
5. Look for architectural patterns (layered, microservices, event-driven, etc.).
6. Evaluate strengths and potential concerns.
7. If it's a flowchart or process: trace the execution path step by step.
</approach>

<output_structure>
**Diagram Overview** (type, scope) → **Components** (organized by layer/subsystem) → **Relationships & Data Flow** → **Architecture Analysis** (patterns, strengths, concerns)

Use Chinese for the response.
</output_structure>"""

# --- 6. 数据图表分析 (对应 analyze_data_visualization) ---
DATA_VIZ_PROMPT = """You are a data analyst with expertise in interpreting data visualizations and extracting meaningful insights.

<task>
Analyze the provided data visualization and extract meaningful insights, trends, patterns, and actionable recommendations.
</task>

<approach>
1. Identify the visualization type and what it's measuring.
2. Read all labels, annotations, axes, legends, and units carefully.
3. Note the time period or categories being displayed.
4. Extract key metrics systematically: max, min, current, averages, notable comparisons.
5. Identify trends and patterns: overall direction, rate of change, cyclicity/seasonality.
6. Look for anomalies and interesting deviations — sudden spikes/drops, outliers.
7. Consider underlying causes and implications.
8. Assess data quality and completeness.
</approach>

<output_structure>
**Visualization Summary** (type, metrics, scope) → **Key Metrics** (current values, peaks, comparisons) → **Trends & Patterns** → **Anomalies & Insights** → **Actionable Recommendations**

Use Chinese for the response.
</output_structure>"""

# --- 7. 通用图片分析 (对应 analyze_image / image_analysis) ---
GENERAL_IMAGE_PROMPT = """You are an advanced AI vision assistant with comprehensive image understanding capabilities.

<task>
Analyze the provided image according to the user's specific instructions and provide a detailed, accurate response.
</task>

<approach>
1. Carefully examine the entire image to understand what it contains.
2. Pay close attention to the user's specific request — tailor your analysis to their needs.
3. Be accurate and honest: only state what you can confidently observe.
4. Provide context and explanation where helpful.
5. Organize your response logically based on the user's request.
</approach>

<output_structure>
**Main Response** (directly address the user's request) → **Detailed Observations** → **Context & Analysis** (if applicable) → **Additional Notes**

Use Chinese for the response.
</output_structure>"""

# ═══════════════════════════════════════════════════════════════
# 核心函数
# ═══════════════════════════════════════════════════════════════


def call_zhipu(image_paths: list[str], system_prompt: str, user_prompt: str = "",
               model: str = "glm-4.6v", max_tokens: int = 2048) -> dict:
    """调用智谱 GLM 视觉 API（不单独用 system 角色，内嵌到 user message）"""
    # 构建完整提示词（匹配 MCP 的做法：system prompt 嵌入 user message 开头）
    full_prompt = ""
    if system_prompt:
        full_prompt += system_prompt + "\n\n---\n\n"
    full_prompt += user_prompt or "请按照上述要求分析图片。用中文回答。"

    content = []
    for p in image_paths:
        b64, mime = encode_image(p)
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    content.append({"type": "text", "text": full_prompt})

    body = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    api_key = get_api_key("zhipu-api-key", "ZHIPU_API_KEY")
    req = urllib.request.Request(
        ZHIPU_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )

    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    elapsed = time.time() - t0
    return {
        "ok": True,
        "api": f"zhipu/{model}",
        "elapsed": elapsed,
        "text": result["choices"][0]["message"]["content"],
        "usage": result.get("usage", {}),
    }


def call_minimax(image_paths: list[str], system_prompt: str, user_prompt: str = "",
                 max_tokens: int = 2048) -> dict:
    """调用 MiniMax M3 视觉 API"""
    # 构建完整提示词（与智谱 API 保持一致）
    full_prompt = ""
    if system_prompt:
        full_prompt += system_prompt + "\n\n---\n\n"
    full_prompt += user_prompt or "请按照上述要求分析图片。"

    content = []
    for p in image_paths:
        b64, mime = encode_image(p)
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    content.append({"type": "text", "text": full_prompt})

    body = {
        "model": "MiniMax-M3",
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "thinking": {"type": "disabled"},  # 关掉 thinking 加速
    }

    api_key = get_api_key("minimax-api-key", "MINIMAX_API_KEY")
    req = urllib.request.Request(
        MINIMAX_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )

    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    elapsed = time.time() - t0

    # MiniMax-M3 可能返回 thinking 标签，提取最终内容
    msg = result["choices"][0]["message"]
    content_text = msg.get("content", "")
    # 去掉 <think>...</think> 标签
    if "<think>" in content_text and "</think>" in content_text:
        end_think = content_text.index("</think>") + len("</think>")
        content_text = content_text[end_think:].strip()

    return {
        "ok": True,
        "api": "minimax/MiniMax-M3",
        "elapsed": elapsed,
        "text": content_text,
        "usage": result.get("usage", {}),
    }


def call_with_fallback(image_paths: list[str], system_prompt: str,
                       user_prompt: str = "", max_tokens: int = 2048) -> dict:
    """优先智谱 glm-4.6v，失败则降级到 MiniMax M3"""
    # 直接使用 glm-4.6v（glm-4v-flash 已废弃，始终返回 400）
    for model in ["glm-4.6v"]:
        try:
            return call_zhipu(image_paths, system_prompt, user_prompt, model=model,
                            max_tokens=max_tokens)
        except Exception as e:
            err = str(e)[:120]
            print(f"  ⚠️ zhipu/{model} 失败: {err}")

    # 降级到 MiniMax
    try:
        return call_minimax(image_paths, system_prompt, user_prompt, max_tokens=max_tokens)
    except Exception as e:
        return {"ok": False, "api": "all", "elapsed": 0, "error": str(e), "text": ""}


# ═══════════════════════════════════════════════════════════════
# 模式映射
# ═══════════════════════════════════════════════════════════════

MODE_MAP = {
    "design":    ("🎨 设计审查", DESIGN_REVIEW_PROMPT),
    "diff":      ("🔍 UI 对比", UI_DIFF_PROMPT),
    "extract":   ("📝 文字提取", TEXT_EXTRACTION_PROMPT),
    "diagnose":  ("🛠 错误诊断", ERROR_DIAGNOSIS_PROMPT),
    "diagram":   ("🏗 技术图解析", DIAGRAM_PROMPT),
    "dataviz":   ("📊 数据图表分析", DATA_VIZ_PROMPT),
    "describe":  ("🖼 通用图片描述", GENERAL_IMAGE_PROMPT),
}

# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="通用图片理解 —— 复刻 zai-mcp-server 全部 7 种工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模式说明 (对应 MCP 工具):
  design    → ui_to_artifact (description)  设计审查
  diff      → ui_diff_check                 两张图对比
  extract   → extract_text_from_screenshot  文字提取 OCR
  diagnose  → diagnose_error_screenshot     错误截图诊断
  diagram   → understand_technical_diagram  技术图解析
  dataviz   → analyze_data_visualization    数据图表分析
  describe  → analyze_image / image_analysis 通用图片描述

API 优先级: glm-4.6v → MiniMax-M3(付费备选)
        """
    )
    parser.add_argument("images", nargs="+", help="图片路径（1张或2张用于diff模式）")
    parser.add_argument("--mode", "-m", choices=list(MODE_MAP.keys()), default="design",
                       help="分析模式 (默认: design)")
    parser.add_argument("--prompt", "-p", type=str, default=None,
                       help="自定义提示词（覆盖内置提示词）")
    parser.add_argument("--max-tokens", "-t", type=int, default=2048,
                       help="最大输出 token (默认: 2048)")
    args = parser.parse_args()

    images = args.images
    mode = args.mode

    # 验证图片
    for p in images:
        if not os.path.isfile(p):
            print(f"❌ 文件不存在: {p}")
            sys.exit(1)

    # 选择提示词
    if args.prompt:
        system_prompt = ""
        user_prompt = args.prompt
        mode_label = "💬 自定义"
    else:
        mode_label, system_prompt = MODE_MAP[mode]
        user_prompt = ""

    # 打印信息
    images_info = ", ".join(f"{os.path.basename(p)} ({os.path.getsize(p)//1024}KB)" for p in images)
    print(f"{mode_label} | 📷 {images_info}")
    print("-" * 60)

    # 调用 API
    result = call_with_fallback(images, system_prompt, user_prompt, max_tokens=args.max_tokens)

    if result["ok"]:
        usage = result.get("usage", {})
        print(f"⏱ {result['elapsed']:.1f}s | 🌐 {result['api']} | "
              f"prompt={usage.get('prompt_tokens','?')} completion={usage.get('completion_tokens','?')}")
        print("-" * 60)
        print(result["text"])
    else:
        print(f"❌ 所有 API 均失败: {result.get('error', 'unknown')}")
        sys.exit(1)

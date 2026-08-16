#!/usr/bin/env python3
"""
批量 OCR 语言检测 — 判断漫画/同人志是中文、日文还是英文。

策略: 单遍采样 5 张图片，OCR 后按字符统计判断：
  - CJK >= 20 → 中文（日文漫画汉字不会这么多而无假名）
  - CJK < 20 且假名/(CJK+假名) > 30% → 日文
  - 否则有 CJK → 中文 / 无 CJK → low_text

缓存: 图片级 OCR 缓存（.ocr_cache.json），重跑秒级完成。

用法:
  uv run python3 detect_language.py             # 全量运行
  uv run python3 detect_language.py --dryrun    # 预览
  uv run python3 detect_language.py --workers 16 # 自定义并发
"""

import subprocess
import os
import sys
import csv
import time
import json
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

OCR_TOOL = os.path.expanduser("~/Applications/local-ocr/ocr_vision")
BASE_DIR = Path("/Volumes/ACASIS/extract")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
OUTPUT_CSV = BASE_DIR / "language_report.csv"
CACHE_FILE = BASE_DIR / ".ocr_cache.json"
SAMPLES_PER_DIR = 5  # 每个目录采样图片数

# ── 图片级 OCR 缓存（线程安全）──────────────────────────────────────────────

_cache_lock = threading.Lock()
_ocr_cache: dict[str, str] = {}

def load_cache() -> dict[str, str]:
    if CACHE_FILE.exists():
        try:
            raw = json.loads(CACHE_FILE.read_text())
            if isinstance(raw, dict):
                # 兼容旧格式：旧格式是 {dir: {lang, ...}}，新格式是 {image_path: text}
                # 检查第一个 value 是否为 dict
                first_val = next(iter(raw.values()), None) if raw else None
                if isinstance(first_val, dict):
                    # 旧格式，清除重来
                    return {}
                return raw
        except Exception:
            pass
    return {}

def save_cache():
    with _cache_lock:
        CACHE_FILE.write_text(json.dumps(_ocr_cache, ensure_ascii=False))

def get_cached_ocr(img_path: str) -> str | None:
    with _cache_lock:
        return _ocr_cache.get(img_path)

def set_cached_ocr(img_path: str, text: str):
    with _cache_lock:
        _ocr_cache[img_path] = text


# ── 字符分析 (复用 local-ocr 的 char_analysis 模块) ─────────────────────

import sys as _sys
_sys.path.insert(0, os.path.expanduser("~/Applications/local-ocr/scripts"))
from char_analysis import is_kana, is_cjk, is_latin, analyze_text, detect_language as _detect_language


def detect_language(texts: list[str]) -> tuple[str, float, str]:
    """Thin wrapper: adds sample text to char_analysis.detect_language output."""
    combined = " ".join(t for t in texts if t.strip())
    sample = combined[:200].replace("\n", " ")
    lang, conf = _detect_language(texts)
    return lang, conf, sample


# ── OCR 调用 ───────────────────────────────────────────────────────────────

def ocr_image(image_path: str) -> str:
    """OCR 单张图片，返回文本（自动使用缓存）"""
    cached = get_cached_ocr(image_path)
    if cached is not None:
        return cached

    try:
        result = subprocess.run(
            [OCR_TOOL, image_path, "cjk", "--raw"],
            capture_output=True, text=True, timeout=15,
        )
        lines = []
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line and not line.startswith("[") and line != "NO TEXT FOUND":
                lines.append(line)
        text = "\n".join(lines)
    except Exception:
        text = ""

    set_cached_ocr(image_path, text)
    return text


# ── 目录发现与采样 ─────────────────────────────────────────────────────────

def find_leaf_dirs(base: Path) -> list[Path]:
    leaf_dirs = []
    for dirpath, dirnames, filenames in os.walk(base):
        if any(skip in dirpath for skip in [".claude", ".git", "__pycache__"]):
            continue
        if any(Path(f).suffix.lower() in IMAGE_EXTS for f in filenames):
            leaf_dirs.append(Path(dirpath))
    return leaf_dirs


def sample_images(dirpath: Path, n: int = SAMPLES_PER_DIR) -> list[Path]:
    """采样 n 张图片，从 20%-80% 位置均匀分布，确保覆盖内容页"""
    images = sorted(
        p for p in dirpath.iterdir()
        if p.suffix.lower() in IMAGE_EXTS and p.is_file()
    )
    if not images:
        return []

    if len(images) <= n:
        return images

    total = len(images)
    start = max(0, int(total * 0.2))
    end = min(total - 1, int(total * 0.8))

    if end - start + 1 < n:
        start, end = 0, total - 1

    if end <= start:
        return [images[total // 2]]

    step = (end - start) / (n + 1)
    idxs = [start + int(step * (i + 1)) for i in range(n)]
    return [images[i] for i in idxs]


# ── 处理单个目录 ───────────────────────────────────────────────────────────

def make_result(dir_key: str, lang: str, confidence: float, sample: str,
                kana: int, cjk: int, latin: int, files: int) -> dict:
    return {
        "dir": dir_key,
        "lang": lang,
        "confidence": round(confidence, 3),
        "kana_count": kana,
        "cjk_count": cjk,
        "latin_count": latin,
        "files_sampled": files,
        "sample_text": sample,
    }


def process_directory(dirpath: Path) -> dict:
    """处理单个目录：采样 → OCR → 判断语言"""
    dir_key = str(dirpath)

    images_all = sorted(
        p for p in dirpath.iterdir()
        if p.suffix.lower() in IMAGE_EXTS and p.is_file()
    )

    if not images_all:
        return make_result(dir_key, "no_images", 0, "", 0, 0, 0, 0)

    # 采样 + OCR
    sampled = sample_images(dirpath, n=SAMPLES_PER_DIR)
    texts = []
    for img in sampled:
        text = ocr_image(str(img))
        if text:
            texts.append(text)

    combined = " ".join(texts)
    kana_count, cjk_count, latin_count = analyze_text(combined)
    lang, confidence, sample = detect_language(texts)

    # 如果 OCR 无结果，标记为 low_text
    if lang == "unknown":
        result = make_result(dir_key, "low_text", 0.0, sample,
                             kana_count, cjk_count, latin_count, len(sampled))
    else:
        result = make_result(dir_key, lang, confidence, sample,
                             kana_count, cjk_count, latin_count, len(sampled))

    return result


# ── 输出 CSV ───────────────────────────────────────────────────────────────

def write_csv(results: list[dict], path: Path):
    fields = [
        "dir", "lang", "confidence",
        "kana_count", "cjk_count", "latin_count",
        "files_sampled", "sample_text",
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)


# ── 主流程 ─────────────────────────────────────────────────────────────────

def main():
    workers = 16
    dryrun = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1])
            i += 2
        elif args[i] == "--dryrun":
            dryrun = True
            i += 1
        else:
            print(f"未知参数: {args[i]}")
            sys.exit(1)

    print(f"🔍 扫描 {BASE_DIR} 中的叶子目录...")
    leaf_dirs = find_leaf_dirs(BASE_DIR)
    print(f"   找到 {len(leaf_dirs)} 个包含图片的目录")

    if dryrun:
        print(f"\n📋 预览模式 — 每目录采样 {SAMPLES_PER_DIR} 张:\n")
        for d in leaf_dirs[:10]:
            s = sample_images(d, n=SAMPLES_PER_DIR)
            print(f"  {d.relative_to(BASE_DIR)}")
            print(f"    采样: {[img.name for img in s]}")
        if len(leaf_dirs) > 10:
            print(f"  ... 还有 {len(leaf_dirs) - 10} 个目录")
        return

    # 加载图片级缓存
    global _ocr_cache
    _ocr_cache = load_cache()
    cached_count = len(_ocr_cache)
    print(f"📦 图片 OCR 缓存: {cached_count} 条")
    estimated_new = max(0, len(leaf_dirs) * SAMPLES_PER_DIR - cached_count)
    print(f"   预计新增 OCR: ~{estimated_new} 次 (约 {estimated_new * 0.3 / workers:.0f}s)")

    total = len(leaf_dirs)
    done = 0
    results = []
    start_time = time.time()
    lang_counts = Counter()

    print(f"🚀 开始单遍 OCR（{workers} 线程，每目录 {SAMPLES_PER_DIR} 张）...\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_directory, d): d for d in leaf_dirs}

        for future in as_completed(futures):
            d = futures[future]
            try:
                r = future.result()
                results.append(r)
                lang_counts[r["lang"]] += 1
            except Exception as e:
                print(f"  ❌ 出错: {d}: {e}")
                results.append(make_result(str(d), "error", 0, str(e), 0, 0, 0, 0))
                lang_counts["error"] += 1

            done += 1
            if done % 100 == 0 or done == total:
                elapsed = time.time() - start_time
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"  [{done}/{total}] {done/total*100:.0f}%  "
                      f"⏱ {elapsed:.0f}s  🏃 {rate:.1f} dir/s  🕐 ETA {eta:.0f}s")

    elapsed = time.time() - start_time
    print(f"\n✅ 完成！耗时 {elapsed:.1f}s")

    results.sort(key=lambda r: r["dir"])
    write_csv(results, OUTPUT_CSV)
    print(f"📄 报告已写入: {OUTPUT_CSV}")
    save_cache()
    print(f"💾 图片缓存已保存 ({len(_ocr_cache)} 条): {CACHE_FILE}")

    # ── 汇总 ──
    print(f"\n📊 语言分布:")
    for lang, count in lang_counts.most_common():
        pct = count / len(results) * 100
        label = {
            "zh": "中文", "ja": "日文", "en": "英文",
            "low_text": "低文字量", "unknown": "未知",
            "error": "错误", "no_images": "无图片",
        }
        print(f"  {label.get(lang, lang):12s} ({lang:10s}): {count:4d} ({pct:.1f}%)")


if __name__ == "__main__":
    main()

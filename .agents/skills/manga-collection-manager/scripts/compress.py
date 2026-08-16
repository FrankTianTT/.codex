#!/usr/bin/env python3
"""
批量压缩：将每个直接含图片的叶子目录压缩为同名 .zip，成功后删除原目录。
用法: uv run python3 compress.py
"""

import subprocess
import os
import sys
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path("/Volumes/ACASIS/extract")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SKIP_DIRS = {"__pycache__", ".claude", ".git"}


def find_leaf_dirs(base: Path) -> list[Path]:
    """找到所有直接包含图片的叶子目录"""
    leaf_dirs = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        p = Path(dirpath)
        has_images = any(
            Path(f).suffix.lower() in IMAGE_EXTS for f in filenames
        )
        if has_images:
            leaf_dirs.append(p)
    return leaf_dirs


def compress_and_remove(dirpath: Path) -> tuple[str, bool, str]:
    """
    压缩目录为同名 zip，成功后删除原目录。
    Returns: (rel_path, success, message)
    """
    rel = str(dirpath.relative_to(BASE_DIR))
    zip_path = dirpath.parent / f"{dirpath.name}.zip"

    # 如果 zip 已存在，跳过
    if zip_path.exists():
        return rel, False, "zip 已存在，跳过"

    try:
        # 切换到目录所在位置，用相对路径压缩（避免 zip 内包含完整路径）
        result = subprocess.run(
            ["zip", "-r", "-q", str(zip_path), dirpath.name],
            cwd=str(dirpath.parent),
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return rel, False, f"zip 失败: {result.stderr.strip()}"

        # 验证 zip 文件大小合理（> 1KB）
        if zip_path.stat().st_size < 1024:
            return rel, False, "zip 文件过小"

        # 删除原目录
        shutil.rmtree(dirpath)
        return rel, True, "✅"
    except subprocess.TimeoutExpired:
        return rel, False, "超时"
    except Exception as e:
        return rel, False, str(e)


def main():
    workers = 8
    dryrun = "--dryrun" in sys.argv

    print("🔍 查找需要压缩的目录...")
    leaf_dirs = find_leaf_dirs(BASE_DIR)
    print(f"   找到 {len(leaf_dirs)} 个目录")

    if dryrun:
        print("\n📋 预览（前20个）:\n")
        for d in leaf_dirs[:20]:
            print(f"  {d.relative_to(BASE_DIR)}")
        if len(leaf_dirs) > 20:
            print(f"  ... 还有 {len(leaf_dirs) - 20} 个")
        return

    total = len(leaf_dirs)
    done = 0
    success = 0
    failed = 0
    skipped = 0

    print(f"🚀 开始压缩（{workers} 线程）...\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(compress_and_remove, d): d for d in leaf_dirs}

        for future in as_completed(futures):
            rel, ok, msg = future.result()
            done += 1
            if ok:
                success += 1
            elif "跳过" in msg:
                skipped += 1
            else:
                failed += 1
                if failed <= 10:
                    print(f"  ❌ {rel}: {msg}")

            if done % 50 == 0 or done == total:
                print(f"  [{done}/{total}] ✅{success} ❌{failed} ⏭{skipped}")

    print(f"\n✅ 完成！成功: {success}, 失败: {failed}, 跳过: {skipped}")


if __name__ == "__main__":
    main()

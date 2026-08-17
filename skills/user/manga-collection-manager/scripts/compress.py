#!/usr/bin/env python3
"""把直接含图片的目录压缩为 ZIP；默认只预览，显式 --execute 才修改文件。"""

import argparse
import os
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_BASE_DIR = Path("/Volumes/ACASIS/extract")
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
SKIP_DIRS = {"__pycache__", ".codex", ".git"}


def find_leaf_dirs(base: Path) -> list[Path]:
    """找到所有直接包含图片的目录。"""
    leaf_dirs = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        has_images = any(Path(f).suffix.lower() in IMAGE_EXTS for f in filenames)
        if has_images and not dirnames:
            leaf_dirs.append(Path(dirpath))
    return leaf_dirs


def source_files(dirpath: Path) -> list[Path]:
    """列出目录内所有普通文件；符号链接单独交给安全检查拒绝。"""
    files: list[Path] = []
    for root, dirnames, filenames in os.walk(dirpath):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        files.extend(Path(root) / name for name in filenames)
    return sorted(files)


def validate_archive(zip_path: Path, expected: dict[str, int]) -> tuple[bool, str]:
    """检查 ZIP CRC、条目名和未压缩大小是否与源目录一致。"""
    try:
        with zipfile.ZipFile(zip_path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                return False, f"压缩包损坏: {bad_member}"
            actual = {
                item.filename: item.file_size
                for item in archive.infolist()
                if not item.is_dir()
            }
    except (OSError, zipfile.BadZipFile) as exc:
        return False, f"无法验证压缩包: {exc}"

    if actual != expected:
        return False, "压缩包条目或文件大小与源目录不一致"
    return True, "ok"


def compress_and_remove(dirpath: Path, base_dir: Path) -> tuple[str, bool, str]:
    """先生成并验证临时 ZIP，再替换正式 ZIP 并删除源目录。"""
    rel = str(dirpath.relative_to(base_dir))
    zip_path = dirpath.parent / f"{dirpath.name}.zip"
    temp_zip = dirpath.parent / f".{dirpath.name}.partial.zip"

    if zip_path.exists():
        return rel, False, "zip 已存在，跳过"

    files = source_files(dirpath)
    if not files:
        return rel, False, "源目录没有可压缩文件"

    blocked = [
        path.relative_to(dirpath)
        for path in files
        if path.is_symlink() or path.suffix.lower() not in IMAGE_EXTS
    ]
    if blocked:
        sample = ", ".join(str(path) for path in blocked[:5])
        suffix = f" 等 {len(blocked)} 个" if len(blocked) > 5 else ""
        return rel, False, f"含非图片文件或符号链接，拒绝压缩并删除源目录: {sample}{suffix}"

    expected = {
        str(Path(dirpath.name) / path.relative_to(dirpath)): path.stat().st_size
        for path in files
    }

    try:
        if temp_zip.exists():
            temp_zip.unlink()
        with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for path in files:
                archive.write(path, arcname=Path(dirpath.name) / path.relative_to(dirpath))

        valid, message = validate_archive(temp_zip, expected)
        if not valid:
            temp_zip.unlink(missing_ok=True)
            return rel, False, message

        temp_zip.replace(zip_path)
        shutil.rmtree(dirpath)
        return rel, True, "✅"
    except Exception as exc:
        temp_zip.unlink(missing_ok=True)
        return rel, False, str(exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE_DIR, help="待压缩根目录")
    parser.add_argument("--workers", type=int, default=8, help="并发线程数")
    parser.add_argument("--execute", action="store_true", help="执行压缩和源目录删除；默认只预览")
    parser.add_argument("--dryrun", action="store_true", help="兼容旧命令；默认行为本来就是预览")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_dir = args.base.expanduser().resolve()

    if not base_dir.is_dir():
        print(f"❌ 根目录不存在: {base_dir}")
        return 2
    if args.workers < 1:
        print("❌ --workers 必须大于 0")
        return 2

    print("🔍 查找需要压缩的目录...")
    leaf_dirs = find_leaf_dirs(base_dir)
    print(f"   找到 {len(leaf_dirs)} 个目录")

    if not args.execute:
        print("\n📋 预览模式；需要修改文件时显式传入 --execute（前20个）：\n")
        for directory in leaf_dirs[:20]:
            print(f"  {directory.relative_to(base_dir)}")
        if len(leaf_dirs) > 20:
            print(f"  ... 还有 {len(leaf_dirs) - 20} 个")
        return 0

    total = len(leaf_dirs)
    done = success = failed = skipped = 0
    print(f"🚀 开始压缩（{args.workers} 线程）...\n")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(compress_and_remove, directory, base_dir): directory
            for directory in leaf_dirs
        }
        for future in as_completed(futures):
            rel, ok, message = future.result()
            done += 1
            if ok:
                success += 1
            elif "跳过" in message:
                skipped += 1
            else:
                failed += 1
                if failed <= 10:
                    print(f"  ❌ {rel}: {message}")
            if done % 50 == 0 or done == total:
                print(f"  [{done}/{total}] ✅{success} ❌{failed} ⏭{skipped}")

    print(f"\n✅ 完成！成功: {success}, 失败: {failed}, 跳过: {skipped}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

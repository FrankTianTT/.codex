#!/usr/bin/env python3
"""从 ImoutoHeaven AList 下载文件，或把本地下载目录与 NAS 交叉比对。

默认只生成预览；只有显式传入 --execute 才创建目录、下载或复制文件。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
import zipfile
from pathlib import Path

import requests


BASE_URL = "https://alist-public.imoutoheaven.org"
API_GET = f"{BASE_URL}/api/fs/get"
HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
DEFAULT_NAS = Path("/Volumes/personal_folder/Private/Manga/单行本")
DEFAULT_DOWNLOADS = Path.home() / "Downloads/manga-downloads"
DEFAULT_MATCH_FILE = Path.home() / "Downloads/alist_match_results.json"
PREFIX = "/SP后端1/离散分发"


NAME_MAP = {
    "石見やそや": "Iwami Yasoya",
    "なしぱすた": "Nashi Pasta",
    "どじろー": "Dojiro",
    "40010試作型": "Shimanto Shisakugata",
    "雨あられ": "Ame Arare",
    "うさぎなごむ": "Usagi Nagomu",
    "しんどう": "Shindou",
    "朝凪": "Asanagi",
    "一宮夕羽": "Ichinomiya Yuuha",
    "黒巣ガタリ": "Kurosu Gatari",
    "酒呑童子": "Shuten Douji",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crossref", action="store_true", help="比对本地下载目录与 NAS")
    parser.add_argument("--execute", action="store_true", help="执行下载或复制；默认只预览")
    parser.add_argument("--nas", type=Path, default=DEFAULT_NAS, help="NAS 漫画根目录")
    parser.add_argument("--downloads", type=Path, default=DEFAULT_DOWNLOADS, help="本地下载根目录")
    parser.add_argument("--match-file", type=Path, default=DEFAULT_MATCH_FILE, help="AList 匹配结果 JSON")
    return parser.parse_args()


def get_zip_files(directory: Path) -> set[str]:
    """列出目录及子目录下的 ZIP 文件名。"""
    files: set[str] = set()
    if not directory.is_dir():
        return files
    for _, _, filenames in os.walk(directory):
        files.update(name for name in filenames if name.lower().endswith(".zip") and not name.startswith("._"))
    return files


def normalize(value: str) -> str:
    return value.lower().replace(" ", "").replace("~", "〜").replace("～", "〜")


def safe_fname(fname: str, max_bytes: int = 200) -> str:
    """在 UTF-8 边界截断过长文件名，并保留扩展名。"""
    base, ext = os.path.splitext(fname)
    encoded = base.encode("utf-8")
    if len(encoded) <= max_bytes:
        return fname
    for index in range(len(encoded[:max_bytes]), 0, -1):
        try:
            return encoded[:index].decode("utf-8") + ext
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法安全截断文件名: {fname}")


def is_dup(fname: str, nas_files: set[str]) -> bool:
    normalized = normalize(fname)
    return fname in nas_files or any(normalize(existing) == normalized for existing in nas_files)


def file_digest(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def validate_zip(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
    except (OSError, zipfile.BadZipFile) as exc:
        raise OSError(f"ZIP 无法读取: {path.name}: {exc}") from exc
    if bad_member:
        raise OSError(f"ZIP CRC 校验失败: {path.name}: {bad_member}")


def atomic_copy(src: Path, dest: Path) -> None:
    """复制到临时文件，验证大小、SHA-256 与 ZIP CRC 后原子提交。"""
    if dest.exists():
        raise FileExistsError(f"目标已存在: {dest}")
    temp = dest.with_name(f".{dest.name}.partial")
    if temp.exists():
        raise FileExistsError(f"残留临时文件: {temp}")
    try:
        shutil.copy2(src, temp)
        if temp.stat().st_size != src.stat().st_size:
            raise OSError("复制后文件大小不一致")
        if file_digest(temp) != file_digest(src):
            raise OSError("复制后 SHA-256 不一致")
        if src.suffix.lower() == ".zip":
            validate_zip(temp)
        os.replace(temp, dest)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def get_download_url(file_path: str) -> str | None:
    """获取签名下载直链。"""
    full_path = PREFIX + file_path
    for attempt in range(3):
        try:
            response = requests.post(
                API_GET,
                headers=HEADERS,
                json={"path": full_path, "password": ""},
                timeout=30,
            )
            payload = response.json()
            if payload.get("code") == 200 and payload.get("data"):
                return payload["data"]["raw_url"]
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"      ⚠️ API 第 {attempt + 1} 次请求失败: {exc}")
            time.sleep(2)
    return None


def mode_alist(nas: Path, match_file: Path, execute: bool) -> int:
    if not nas.is_dir():
        print(f"❌ NAS 目录不存在或卷未挂载: {nas}")
        return 2
    if not match_file.is_file():
        print(f"❌ 匹配结果不存在: {match_file}")
        return 2

    data = json.loads(match_file.read_text(encoding="utf-8"))
    matched = data.get("matched", {})
    to_download: list[tuple[str, dict]] = []
    for author_dir in sorted(matched):
        nas_files = get_zip_files(nas / author_dir)
        for remote_file in matched[author_dir]:
            if not is_dup(remote_file["name"], nas_files):
                to_download.append((author_dir, remote_file))

    total_size = sum(item["size"] for _, item in to_download) / (1024**2)
    print(f"📥 待下载 {len(to_download)} 个文件，约 {total_size:.0f} MB")
    for author_dir, remote_file in to_download[:50]:
        print(f"  [{author_dir}] {remote_file['name']} ({remote_file['size'] / 1024**2:.0f} MB)")
    if len(to_download) > 50:
        print(f"  …其余 {len(to_download) - 50} 个")
    if not execute:
        print("📋 预览模式；确认清单后使用 --execute。")
        return 0

    downloaded = 0
    failures: list[str] = []
    for author_dir, remote_file in to_download:
        url = get_download_url(remote_file["path"])
        if not url:
            failures.append(f"{author_dir}/{remote_file['name']}: 无法获取下载地址")
            continue

        dest_dir = nas / author_dir / "散篇"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / safe_fname(remote_file["name"])
        temp = dest.with_name(f".{dest.name}.partial")
        if dest.exists() or temp.exists():
            failures.append(f"{dest}: 目标或临时文件已存在，拒绝覆盖")
            continue

        success = False
        for attempt in range(5):
            try:
                response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=300, stream=True)
                if response.status_code == 429:
                    time.sleep((attempt + 1) * 10)
                    url = get_download_url(remote_file["path"])
                    if not url:
                        break
                    continue
                response.raise_for_status()
                with temp.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
                if temp.stat().st_size != remote_file["size"]:
                    raise OSError("下载大小与 AList 元数据不一致")
                validate_zip(temp)
                os.replace(temp, dest)
                downloaded += 1
                success = True
                break
            except (OSError, requests.RequestException) as exc:
                temp.unlink(missing_ok=True)
                if attempt == 4:
                    failures.append(f"{dest}: {exc}")
                else:
                    time.sleep(5)
                    url = get_download_url(remote_file["path"]) or url
        if success:
            print(f"✅ {dest}")
        time.sleep(3)

    print(f"完成：成功 {downloaded}，失败 {len(failures)}")
    for failure in failures[:20]:
        print(f"  ❌ {failure}")
    return 1 if failures else 0


def mode_crossref(downloads: Path, nas: Path, execute: bool) -> int:
    if not downloads.is_dir():
        print(f"❌ 下载目录不存在: {downloads}")
        return 2
    if not nas.is_dir():
        print(f"❌ NAS 目录不存在或卷未挂载: {nas}")
        return 2

    plans: list[tuple[Path, Path]] = []
    planned_destinations: set[Path] = set()
    conflicts: list[str] = []
    new_authors: list[tuple[str, int]] = []
    for download_author in sorted(downloads.iterdir()):
        if not download_author.is_dir() or download_author.name.startswith("."):
            continue
        local_files = get_zip_files(download_author)
        if not local_files:
            continue

        nas_name = NAME_MAP.get(download_author.name, download_author.name)
        nas_author = nas / nas_name
        if not nas_author.is_dir():
            match = next((item for item in nas.iterdir() if item.is_dir() and normalize(item.name) == normalize(nas_name)), None)
            if match is None:
                new_authors.append((download_author.name, len(local_files)))
                continue
            nas_author = match

        nas_files = get_zip_files(nas_author)
        for source in download_author.rglob("*"):
            if not source.is_file() or source.suffix.lower() != ".zip":
                continue
            if source.name.startswith("._") or is_dup(source.name, nas_files):
                continue
            destination = nas_author / "散篇" / safe_fname(source.name)
            if destination in planned_destinations:
                conflicts.append(f"截断后目标重名: {destination}")
                continue
            planned_destinations.add(destination)
            plans.append((source, destination))

    print(f"📦 待复制 {len(plans)} 个文件；未收录作者 {len(new_authors)} 位；冲突 {len(conflicts)} 个")
    for src, dest in plans[:50]:
        print(f"  {src} -> {dest}")
    for name, count in new_authors[:20]:
        print(f"  ⏭️ 未收录作者：{name}（{count} 个 ZIP）")
    for conflict in conflicts[:20]:
        print(f"  ❌ {conflict}")
    if not execute:
        print("📋 预览模式；没有创建目录或复制文件。确认后使用 --crossref --execute。")
        return 1 if conflicts else 0

    if conflicts:
        print("❌ 存在目标冲突，拒绝执行整批复制。")
        return 1

    failures: list[str] = []
    for src, dest in plans:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            atomic_copy(src, dest)
            print(f"✅ {dest}")
        except (OSError, zipfile.BadZipFile) as exc:
            failures.append(f"{src}: {exc}")
    for failure in failures[:20]:
        print(f"  ❌ {failure}")
    return 1 if failures else 0


def main() -> int:
    args = parse_args()
    nas = args.nas.expanduser().resolve()
    if args.crossref:
        return mode_crossref(args.downloads.expanduser().resolve(), nas, args.execute)
    return mode_alist(nas, args.match_file.expanduser().resolve(), args.execute)


if __name__ == "__main__":
    raise SystemExit(main())

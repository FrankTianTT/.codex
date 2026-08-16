#!/usr/bin/env python3
"""
从 ImoutoHeaven AList 下载匹配的同人志到 NAS，含本地交叉比对模式。

用法:
  uv run --with requests python3 alist_download.py               # AList 下载预览
  uv run --with requests python3 alist_download.py --execute     # AList 下载执行
  uv run --with requests python3 alist_download.py --crossref    # 本地目录交叉比对预览
  uv run --with requests python3 alist_download.py --crossref --execute  # 比对+拷贝执行
"""
import os, sys, json, time, shutil, requests

BASE_URL = 'https://alist-public.imoutoheaven.org'
API_GET = f'{BASE_URL}/api/fs/get'
API_LIST = f'{BASE_URL}/api/fs/list'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'}
NAS = "/Volumes/personal_folder/Private/Manga/单行本"
DL = "/Users/frank/Downloads/manga-downloads"
MATCH_FILE = "/Users/frank/Downloads/alist_match_results.json"
PREFIX = '/SP后端1/离散分发'

# 画师名映射：日文 ↔ Romaji
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

# ── 工具函数 ─────────────────────────────────────────────────────────

def get_zip_files(directory):
    """列出目录及子目录下所有 ZIP 文件（basename 集合）"""
    files = set()
    if not os.path.isdir(directory):
        return files
    for root, dirs, filenames in os.walk(directory):
        for f in filenames:
            if f.endswith('.zip') and not f.startswith('._'):
                files.add(f)
    return files

def normalize(s):
    """归一化文件名以做模糊比对"""
    return s.lower().replace(' ', '').replace('~', '〜').replace('～', '〜')

def safe_fname(fname, max_bytes=200):
    """截断过长文件名，保留 UTF-8 边界和扩展名"""
    base, ext = os.path.splitext(fname)
    encoded = base.encode('utf-8')
    if len(encoded) <= max_bytes:
        return fname
    for i in range(len(encoded[:max_bytes]) - 1, max(0, len(encoded[:max_bytes]) - 10), -1):
        try:
            return encoded[:i].decode('utf-8') + ext
        except UnicodeDecodeError:
            continue
    return base[:80] + ext

def is_dup(fname, nas_files):
    """检查文件是否已在 NAS 存在（精确 + 归一化比对）"""
    if fname in nas_files:
        return True
    norm = normalize(fname)
    return any(normalize(nf) == norm for nf in nas_files)

# ── AList API ─────────────────────────────────────────────────────────

def get_download_url(file_path):
    """获取签名下载直链（3 次重试）"""
    full_path = PREFIX + file_path
    for attempt in range(3):
        try:
            resp = requests.post(API_GET, headers=HEADERS,
                                json={'path': full_path, 'password': ''}, timeout=30)
            j = resp.json()
            if j['code'] == 200 and j['data']:
                return j['data']['raw_url']
        except Exception as e:
            print(f"      ⚠️ API attempt {attempt+1}: {e}")
            time.sleep(2)
    return None

# ── 模式 1：AList 下载 ────────────────────────────────────────────────

def mode_alist(dry_run=True):
    DELAY = 3.0

    with open(MATCH_FILE, 'r', encoding='utf-8') as fp:
        data = json.load(fp)

    matched = data['matched']

    to_download = []
    for author_dir in sorted(matched):
        nas_files = get_zip_files(os.path.join(NAS, author_dir))
        for rf in matched[author_dir]:
            if not is_dup(rf['name'], nas_files):
                to_download.append((author_dir, rf))

    if not to_download:
        print("✅ 所有文件已下载完毕！")
        return

    total_size = sum(rf['size'] for _, rf in to_download) / (1024**2)
    print(f"📥 {len(to_download)} files remaining ({total_size:.0f} MB)\n")

    if dry_run:
        for author_dir, rf in to_download:
            print(f"   [{author_dir}] {rf['name'][:90]} ({rf['size']/1024**2:.0f} MB)")
        print(f"\n⚠️ DRY RUN。执行下载: python3 {sys.argv[0]} --execute")
        return

    downloaded, failed, total_bytes = 0, [], 0

    for i, (author_dir, rf) in enumerate(to_download):
        fname = rf['name']
        size_mb = rf['size'] / (1024**2)
        print(f"[{i+1}/{len(to_download)}] 📥 [{author_dir}] {fname[:80]}... ({size_mb:.0f} MB)", end="", flush=True)

        url = get_download_url(rf['path'])
        if not url:
            print(" ❌ URL获取失败")
            failed.append((author_dir, rf, "URL获取失败"))
            continue

        dest_dir = os.path.join(NAS, author_dir, "散篇")
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, safe_fname(fname))
        tmp_path = dest_path + ".tmp"

        success = False
        for attempt in range(5):
            try:
                dl_resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'},
                                       timeout=300, stream=True)

                if dl_resp.status_code == 429:
                    wait = (attempt + 1) * 10
                    print(f" ⏳ 429 等待{wait}s...", end="", flush=True)
                    time.sleep(wait)
                    url = get_download_url(rf['path'])
                    if not url:
                        break
                    continue

                dl_resp.raise_for_status()

                with open(tmp_path, 'wb') as fp:
                    for chunk in dl_resp.iter_content(chunk_size=8192):
                        fp.write(chunk)

                actual_size = os.path.getsize(tmp_path)
                if actual_size == rf['size']:
                    os.rename(tmp_path, dest_path)
                    print(f" ✅ {actual_size/1024**2:.0f}MB")
                    downloaded += 1
                    total_bytes += actual_size
                    success = True
                    break
                else:
                    print(f" ⚠️ 大小不符 ({actual_size} vs {rf['size']})")
                    os.remove(tmp_path)
                    if attempt < 2:
                        url = get_download_url(rf['path'])

            except Exception as e:
                if attempt < 4:
                    print(f" 🔄 retry {attempt+1}...", end="", flush=True)
                    time.sleep(5)
                    url = get_download_url(rf['path'])
                else:
                    print(f" ❌ {str(e)[:80]}")

        if not success:
            failed.append((author_dir, rf, "下载失败"))
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        time.sleep(DELAY)

    print(f"\n{'='*60}")
    print(f"✅ 下载: {downloaded} files, {total_bytes/1024**2:.0f} MB ({total_bytes/1024**3:.1f} GB)")
    if failed:
        print(f"❌ 失败: {len(failed)} files")
        for author_dir, rf, reason in failed[:10]:
            print(f"   [{author_dir}] {rf['name'][:80]}... — {reason}")

# ── 模式 2：本地交叉比对 ──────────────────────────────────────────────

def mode_crossref(dry_run=True):
    if dry_run:
        print("🔍 DRY RUN — 使用 --execute 执行实际拷贝\n")

    results = []

    for dl_name in sorted(os.listdir(DL)):
        dl_path = os.path.join(DL, dl_name)
        if not os.path.isdir(dl_path) or dl_name.startswith('.'):
            continue

        dl_files = get_zip_files(dl_path)
        if not dl_files:
            continue

        nas_name = NAME_MAP.get(dl_name, dl_name)
        nas_path = os.path.join(NAS, nas_name)

        if not os.path.isdir(nas_path):
            for d in os.listdir(NAS):
                if normalize(d) == normalize(nas_name):
                    nas_path = os.path.join(NAS, d)
                    nas_name = d
                    break

        if not os.path.isdir(nas_path):
            results.append((dl_name, "new_author", len(dl_files), 0, 0))
            continue

        nas_files = get_zip_files(nas_path)
        new_files, dup_count = [], 0

        for f in dl_files:
            if is_dup(f, nas_files):
                dup_count += 1
            else:
                new_files.append(f)

        if new_files:
            dest_dir = os.path.join(nas_path, "散篇")
            os.makedirs(dest_dir, exist_ok=True)

            if not dry_run:
                for f in new_files:
                    for root, dirs, filenames in os.walk(dl_path):
                        if f in filenames:
                            src = os.path.join(root, f)
                            dest = os.path.join(dest_dir, f)
                            if not os.path.exists(dest):
                                shutil.copy2(src, dest)
                            break

            print(f"📦 [{dl_name}] → [{nas_name}]: {len(new_files)} 新 / {dup_count} 重复 / {len(dl_files)} 总计")
            for f in new_files:
                print(f"   ➕ {f[:90]}")
        else:
            print(f"⏭️ [{dl_name}] → [{nas_name}]: 全部重复 ({len(dl_files)} files)")

        results.append((dl_name, "matched", len(dl_files), len(new_files), dup_count))

    print(f"\n{'='*60}")
    total_new = sum(r[3] for r in results)
    new_authors = [r for r in results if r[1] == "new_author"]
    print(f"已收录作者新增: {total_new} 文件")
    if new_authors:
        print(f"新作者 (未收录): {len(new_authors)} 位 / {sum(r[2] for r in new_authors)} 文件")
        for name, _, count, _, _ in new_authors:
            print(f"   [{name}] {count} ZIPs")

    if dry_run:
        print(f"\n⚠️ DRY RUN。执行拷贝: python3 {sys.argv[0]} --crossref --execute")

# ── 入口 ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    crossref = "--crossref" in sys.argv

    if crossref:
        mode_crossref(dry_run=dry_run)
    else:
        mode_alist(dry_run=dry_run)

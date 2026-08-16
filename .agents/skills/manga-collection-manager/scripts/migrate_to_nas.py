#!/usr/bin/env python3
"""迁移漫画 ZIP；默认只预览，显式 --execute 才复制并删除源文件。"""
import argparse
import hashlib
import os
import re
import shutil
import zipfile
from collections import defaultdict

SRC = "/Volumes/ACASIS"
DST_AUTHORS = "/Volumes/personal_folder/Private/Manga/单行本"
DST_MAGAZINE = "/Volumes/personal_folder/Private/Manga/杂志"

# Author alias mapping
AUTHOR_ALIAS = {
    "ぼっしぃ": "Bosshi", "ぼっしぃ": "Bosshi",
    "あきのそら": "Akino Sora",
    "かいづか": "Kaiduka",
    "くっきおーれ": "Kyockcho", "きょくちょ": "Kyockcho",
    "みちきんぐ": "Michiking", "みちきんぐ": "Michiking",
    "もず": "Mozu", "もず": "Mozu",
    "もみ": "momi",
    "ななお": "Nanao",
    "さいもん": "Saimon",
    "えのきど": "Enokido",
    "いわみやそや": "Iwami Yasoya",
    "はまお": "Hamao",
    "めのこ": "Menoko",
    "Clone人間": "clone人間",
    "たつか": "Do well !!! (たつか)",
    "オクモト悠太": "Okumoto Yuuta",
    "ポン貴花田": "Pon Takahada",
    "栗福みのる": "Kurifuku Minoru",
    "宮部キウイ": "Miyabe Kiwi",
    "石見やそや": "Iwami Yasoya",
    "波乗かもめ": "Naminori Kamome",
    "紅端よどむ": "Kurenai Yodomu",
    "赤月みゅうと": "Akatsuki Myuuto",
    "ひなづか凉": "雛咲葉",
    "あずせ": "あずせ",
    "しのざき嶺": None,
    "さじぺん": None,
    "あべもりおか": None,
}

# Known recommended new authors (curated from report 🔥)
KNOWN_NEW = {
    "うるし原智志", "八月薫", "Cuvie", "仔縞楽々", "たかやKi",
    "TYPE.90", "板場広し", "海野螢", "藤坂リリック", "砂漠",
    "横山ミチル", "七尾ゆきじ", "まめおじたん", "いのまる",
    "チグチミリ", "ぐすたふ",
    "皐月芋網", "黒田くろた", "柚木N", "飛燕",
    "堀江耽閨", "越山弱衰", "井上よしひさ", "英丸",
    "春城秋介", "道満晴明", "町田ひらく",
    "トロ太郎", "山田タヒチ", "砂藤シュガー", "目高健一",
    "宏式", "格闘王国", "干支門三十四", "児妻",
    "朝比奈まこと", "みかんR", "伊達レン", "長い草", "わり子",
    "SINK", "TANABE", "春輝", "琴義弓介", "鉢本", "黒ノ樹",
    "龍牙翔", "DISTANCE", "clone人間", "世徒ゆうき",
    "立花オミナ", "gonza", "復八磨直兎", "東磨樹",
    "松河", "まるキ堂", "速野悠二", "秋乃秀文", "めの子",
    "高野真之", "骨太男爵", "黒金さつき", "鶴山ミト",
    "鶴亀まよ", "和馬村政", "縞浦", "腐蝕", "富士やま",
    "荒岸来歩", "堺はまち", "エロ井ロエ",
    "鈴月あこに", "なるさわ景", "井雲くす", "ウエノ直哉",
    "汐乃コウ", "玄鉄絢", "跳馬遊鹿", "無色三太郎",
    "土肥泥助", "町内福引犬 (るぅ1mm)", "由良橋勢",
    "柚十扇", "雨山電信", "よそ者",
    "Kima-gray", "伊月クロ", "大和川", "桂よしひろ", "犬",
    "星野竜一", "chaccu", "大暮維人", "艶々", "飛龍乱",
    "葵ヒトリ", "彦馬ヒロユキ", "EBA", "BANG-YOU",
    "Butcha-U", "山文京伝", "鬼姫", "彩画堂", "石恵",
    "田亀源五郎", "KAKERU", "RED-RUM", "針金紳士",
    "前島龍", "犬星", "染岡ゆすら", "仁嶋中道",
    "朝野よみち", "内藤キララ", "南乃さざん",
    "宮元一佐", "宇行日和", "蛙子丁字", "下平十子",
    "木静謙二", "山田J太",
    "朝峰テル", "杜若つくね", "岡田コウ",
    "東野みかん", "茶野みな", "吹浦ハギ",
    "chin", "inono", "クロFn", "Ash横島", "メメ50",
    "TAKUMI", "T.K-1", "SAS", "Rico", "NABURU",
    "カワディMAX", "LAZY CLUB", "ジョン・K・ペー太",
    "KEN", "Karl", "Kanten", "Jun", "IAPOC",
    "H-magic", "GEN", "FEENA", "doumou",
    "BUTA", "AKIRA", "ACはせべ", "5thルナ",
    "peachpulsar (みら)", "Toranoana", "tatapopo",
    "赤月みゅうと",
}

MAGAZINE_PATTERNS = {
    "COMIC BAVEL": [r'^COMIC BAVEL'],
    "Dascomi": [r'^ダスコミ|^ダスコミ'],
    "WEEKLY快楽天": [r'^WEEKLY快楽天'],
    "別冊コミックアンリアル": [r'^別冊コミックアンリアル'],
    "二次元コミックマガジン": [r'^二次元コミックマガジン'],
    "アンソロジー": [r'アンソロジー|アンソロジー|総集編|Omnibus'],
    "その他雑誌": [r'^乱漫|^催ぷに|^デジタルぷに|^カラミざかり|^制服娼館|^親子百合|^異世界ド修羅場|^ボールド|^図解天王|^诗词动物城'],
}

MAX_FNAME_BYTES = 200  # safe limit for filename component


def extract_author(fname):
    m = re.match(r'^\[([^\]]+)\]', fname)
    return m.group(1) if m else None


def classify_magazine(fname):
    base = fname.replace('.zip', '')
    for dirname, patterns in MAGAZINE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, base):
                return dirname
    return None


def normalize_name(name):
    if name is None:
        return None
    return name.lower().replace(' ', '').replace('・', '').replace('‧', '').replace('゙', '').replace('゚', '')


def find_existing_dir(author_name, existing_dirs):
    if author_name in AUTHOR_ALIAS:
        mapped = AUTHOR_ALIAS[author_name]
        if mapped and mapped in existing_dirs:
            return mapped
    if author_name in existing_dirs:
        return author_name
    norm = normalize_name(author_name)
    for d in existing_dirs:
        if normalize_name(d) == norm:
            return d
        if len(norm) > 2 and len(normalize_name(d)) > 2:
            if norm in normalize_name(d) or normalize_name(d) in norm:
                return d
    return None


def safe_fname(fname, max_bytes=MAX_FNAME_BYTES):
    """Truncate filename if too long, preserving extension."""
    base, ext = os.path.splitext(fname)
    encoded = base.encode('utf-8')
    if len(encoded) <= max_bytes:
        return fname
    # Truncate, trying to keep on a UTF-8 boundary
    truncated = encoded[:max_bytes]
    # Decode back, ignoring incomplete chars at end
    try:
        new_base = truncated.decode('utf-8')
    except UnicodeDecodeError:
        # Cut back until valid
        for i in range(len(truncated) - 1, len(truncated) - 5, -1):
            try:
                new_base = truncated[:i].decode('utf-8')
                break
            except UnicodeDecodeError:
                continue
        else:
            new_base = base[:80]  # fallback
    return new_base + ext


def file_digest(path, chunk_size=1024 * 1024):
    """计算文件 SHA-256，用于跨卷复制后的完整性验证。"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def safe_move(src, dst_dir, fname):
    """跨卷复制，校验大小与 SHA-256 后才删除源文件。"""
    safe_name = safe_fname(fname)
    dest = os.path.join(dst_dir, safe_name)

    if os.path.exists(dest):
        try:
            if (
                os.path.getsize(dest) == os.path.getsize(src)
                and file_digest(dest) == file_digest(src)
            ):
                return False, "already_exists"
        except OSError:
            pass
        return False, "destination_conflict"

    tmp = dest + ".tmp"
    try:
        shutil.copy2(src, tmp)
        if os.path.getsize(tmp) != os.path.getsize(src):
            raise OSError("复制后文件大小不一致")
        if file_digest(tmp) != file_digest(src):
            raise OSError("复制后 SHA-256 不一致")
        if src.lower().endswith(".zip"):
            with zipfile.ZipFile(tmp) as archive:
                bad_member = archive.testzip()
            if bad_member:
                raise OSError(f"ZIP 完整性检查失败: {bad_member}")
        os.replace(tmp, dest)
        os.remove(src)
        return True, safe_name
    except OSError as e:
        # Clean up temp file on failure
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        return False, str(e)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", default=SRC, help="来源卷或目录")
    parser.add_argument("--dst-authors", default=DST_AUTHORS, help="作者目标目录")
    parser.add_argument("--dst-magazine", default=DST_MAGAZINE, help="杂志目标目录")
    parser.add_argument("--execute", action="store_true", help="执行复制和源文件删除；默认只预览")
    parser.add_argument("--dryrun", action="store_true", help="兼容旧命令；默认行为本来就是预览")
    return parser.parse_args()


def main():
    global SRC, DST_AUTHORS, DST_MAGAZINE
    args = parse_args()
    SRC = os.path.abspath(os.path.expanduser(args.src))
    DST_AUTHORS = os.path.abspath(os.path.expanduser(args.dst_authors))
    DST_MAGAZINE = os.path.abspath(os.path.expanduser(args.dst_magazine))

    for label, path in (
        ("来源", SRC),
        ("作者目标", DST_AUTHORS),
        ("杂志目标", DST_MAGAZINE),
    ):
        if not os.path.isdir(path):
            print(f"❌ {label}目录不存在或卷未挂载: {path}")
            return 2

    existing_dirs = set()
    for d in os.listdir(DST_AUTHORS):
        if os.path.isdir(os.path.join(DST_AUTHORS, d)) and not d.startswith('.'):
            existing_dirs.add(d)

    new_files = []
    for i in range(1, 13):
        d = os.path.join(SRC, f"{i:02d}")
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if f.endswith('.zip') and not f.startswith('._'):
                new_files.append((os.path.join(d, f), f))

    # Categorize
    to_existing = defaultdict(list)
    to_new = defaultdict(list)
    to_magazine = defaultdict(list)
    skipped = []

    for src_path, fname in new_files:
        author = extract_author(fname)
        mag = classify_magazine(fname)

        if mag and not author:
            to_magazine[mag].append((src_path, fname))
            continue

        if author:
            existing_dir = find_existing_dir(author, existing_dirs)
            if existing_dir:
                dest_check = os.path.join(DST_AUTHORS, existing_dir, safe_fname(fname))
                if os.path.exists(dest_check):
                    skipped.append((fname, f"已存在 [{existing_dir}]"))
                else:
                    to_existing[existing_dir].append((src_path, fname))
            elif author in KNOWN_NEW:
                dest_check = os.path.join(DST_AUTHORS, author, safe_fname(fname))
                if os.path.exists(dest_check):
                    skipped.append((fname, f"已存在 [{author}]"))
                else:
                    to_new[author].append((src_path, fname))
            else:
                skipped.append((fname, f"非知名 [{author}]"))
        else:
            if mag:
                to_magazine[mag].append((src_path, fname))
            else:
                skipped.append((fname, "无法分类"))

    total_exist = sum(len(v) for v in to_existing.values())
    total_new = sum(len(v) for v in to_new.values())
    total_mag = sum(len(v) for v in to_magazine.values())

    print(f"📌 已有作者: {total_exist} 部 / {len(to_existing)} 位")
    print(f"🆕 新作者:   {total_new} 部 / {len(to_new)} 位")
    print(f"📖 杂志:     {total_mag} 部 / {len(to_magazine)} 个分类")
    print(f"⏭️ 跳过:     {len(skipped)} 部")
    print()

    if not args.execute:
        print("📋 预览模式；需要迁移并删除源文件时显式传入 --execute。")
        for label, groups in (
            ("已有作者", to_existing),
            ("新作者", to_new),
            ("杂志", to_magazine),
        ):
            shown = 0
            for destination, files in sorted(groups.items()):
                for _, fname in files:
                    print(f"  {label}: {fname} -> {destination}/")
                    shown += 1
                    if shown >= 10:
                        break
                if shown >= 10:
                    break
        return 0

    errors = []

    # Move existing author files
    for author_dir in sorted(to_existing.keys()):
        files = to_existing[author_dir]
        dest_d = os.path.join(DST_AUTHORS, author_dir)
        os.makedirs(dest_d, exist_ok=True)
        ok = 0
        for src_path, fname in files:
            success, _ = safe_move(src_path, dest_d, fname)
            if success:
                ok += 1
            else:
                errors.append((fname, _))
        if ok:
            print(f"  ✅ [{author_dir}] +{ok} 部")

    # Move new author files
    for author in sorted(to_new.keys()):
        files = to_new[author]
        dest_d = os.path.join(DST_AUTHORS, author)
        os.makedirs(dest_d, exist_ok=True)
        ok = 0
        for src_path, fname in files:
            success, _ = safe_move(src_path, dest_d, fname)
            if success:
                ok += 1
            else:
                errors.append((fname, _))
        if ok:
            print(f"  🆕 [{author}] +{ok} 部")

    # Move magazine files
    for mag in sorted(to_magazine.keys()):
        files = to_magazine[mag]
        dest_d = os.path.join(DST_MAGAZINE, mag)
        os.makedirs(dest_d, exist_ok=True)
        ok = 0
        for src_path, fname in files:
            success, _ = safe_move(src_path, dest_d, fname)
            if success:
                ok += 1
            else:
                errors.append((fname, _))
        if ok:
            print(f"  📖 [{mag}] +{ok} 部")

    moved = total_exist + total_new + total_mag - len(errors)
    print(f"\n{'='*60}")
    print(f"✅ 迁移: {moved} 部")
    print(f"⏭️ 跳过: {len(skipped)} 部")
    if errors:
        print(f"⚠️ 错误: {len(errors)} 部")
        for fname, reason in errors[:10]:
            print(f"   ⚠️ {fname[:80]}... — {reason}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

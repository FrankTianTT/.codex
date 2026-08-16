#!/usr/bin/env python3
"""Migrate manga v2 — with long filename handling and resume support."""
import os, re, shutil, sys
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


def safe_move(src, dst_dir, fname):
    """Move file across devices with long filename handling."""
    safe_name = safe_fname(fname)
    dest = os.path.join(dst_dir, safe_name)

    if os.path.exists(dest):
        # Verify file integrity by comparing size
        try:
            if os.path.getsize(dest) == os.path.getsize(src):
                return False, "already_exists"
        except OSError:
            pass
        # Size differs or unreadable — overwrite with temp+rename to be safe

    tmp = dest + ".tmp"
    try:
        shutil.copy2(src, tmp)
        os.rename(tmp, dest)  # atomic on same filesystem
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


def main():
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


if __name__ == "__main__":
    main()

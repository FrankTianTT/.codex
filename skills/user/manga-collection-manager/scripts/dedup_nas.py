#!/usr/bin/env python3
"""去重脚本 — 默认预览；--execute 时把重复文件移入可恢复隔离目录。"""
import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE = "/Volumes/personal_folder/Private/Manga/单行本"

# 去重规则: { author_dir: { "作品关键词": "保留的文件名关键词" } }
# 匹配逻辑: 文件名包含"作品关键词"且包含"保留关键词"的→保留，其余同作品→删除

RULES = [
    # === P0 第一梯队 ===
    {
        "author": "飛燕",
        "work_key": "いっぱいイってね♪勇者さま",
        "keep_key": "restday111去码+超分",
        "note": "3份→保留超分去码版"
    },
    {
        "author": "kakao",
        "work_key": "独身ハンターの出逢いはエルフの森",
        "keep_key": "1-5&後日談",
        "note": "5份→保留最完整版(含1-5+后日谈)"
    },
    {
        "author": "児妻",
        "work_key": "金曜日の母たちへ",
        "keep_key": "[v4]",
        "note": "v2/v3/v4→保留v4最新版"
    },
    {
        "author": "Croriin",
        "work_key": "ヤリこみクロニクル",
        "keep_key": "无毒汉化组",
        "note": "3份→保留无毒汉化组无修正版"
    },
    {
        "author": "水龍敬",
        "work_key": "貞操観念ゼロの女友達",
        "keep_key": "[中国翻訳].zip",
        "note": "3份→保留纯[中国翻訳]版(不含其他后缀)"
    },
    {
        "author": "Kurenai Yodomu",
        "work_key": "江藤さん",
        "keep_key": "無修正",
        "note": "2份→保留無修正DL版"
    },
    {
        "author": "七尾ゆきじ",
        "work_key": "雌の本能に逆らえない",
        "keep_key": "[中国翻訳] [無修正] [DL版]",
        "note": "3份→保留标准版"
    },
    {
        "author": "Naminori Kamome",
        "work_key": "雪ふって、恋かたまる",
        "keep_key": "[中国翻訳] [無修正] [DL版]",
        "note": "3份→保留标准版"
    },
    # === P1 第二梯队 ===
    {
        "author": "世徒ゆうき",
        "work_key": "千歳",
        "keep_key": "[無修正]",
        "note": "2份→保留無修正版"
    },
    {
        "author": "伊達レン",
        "work_key": "ネトリコン",
        "keep_key": "桃紫の汉化",
        "note": "3份→人工复核，暂保留桃紫版(带汉化组名更可信)"
    },
    {
        "author": "墓場",
        "work_key": "女教師市川美由紀",
        "keep_key": "BLUE氪个人翻译",
        "note": "3份→保留BLUE氪重嵌版"
    },
    {
        "author": "DATE",
        "work_key": "同居する粘液",
        "keep_key": "第1-12話 2体目-第1-5話",
        "note": "3份→保留最完整版"
    },
    {
        "author": "Bosshi",
        "work_key": "お嬢様はHがお好き",
        "keep_key": "时空汉化组",
        "note": "保留时空汉化组版"
    },
    {
        "author": "Bosshi",
        "work_key": "ちゅ～ちゅ～ちぇり～",
        "keep_key": "字圖坊",
        "note": "保留字圖坊DL版"
    },
    {
        "author": "たかやKi",
        "work_key": "年下しんどろ～む",
        "keep_key": "[無修正]",
        "note": "保留無修正版"
    },
    {
        "author": "たかやKi",
        "work_key": "恋糸記念日",
        "keep_key": "[無修正]",
        "note": "保留無修正版"
    },
    {
        "author": "Kurifuku Minoru",
        "work_key": "時間停止",
        "keep_key": "ストップ",
        "note": "保留日文标题版"
    },
    {
        "author": "春城秋介",
        "work_key": "実娘の代わりに好きなだけ",
        "keep_key": "&",
        "note": "保留 & 版"
    },
    {
        "author": "松河",
        "work_key": "貴方の専属ソープ嬢",
        "keep_key": "[無修正]",
        "note": "保留無修正版"
    },
    {
        "author": "板場広し",
        "work_key": "押しかけ母性ほなみちゃん",
        "keep_key": "[無修正]",
        "note": "保留無修正版"
    },
    {
        "author": "saitom",
        "work_key": "いっしょにしよ",
        "keep_key": "いっしょにしよ [中国翻訳]",
        "note": "保留日文标题版"
    },
    # === P1 第三梯队 ===
    {
        "author": "Okumoto Yuuta",
        "work_key": "パイらびゅ",
        "keep_key": "！",
        "note": "保留全角感叹号版"
    },
    {
        "author": "如月群真",
        "work_key": "好きになったら一直線",
        "keep_key": "[無修正]",
        "note": "保留無修正版"
    },
    {
        "author": "柚十扇",
        "work_key": "いっぱいさわって",
        "keep_key": "[無修正]",
        "note": "保留無修正版"
    },
    {
        "author": "高野真之",
        "work_key": "いけないよ、佐藤先生",
        "keep_key": "[無修正]",
        "note": "保留無修正版"
    },
    {
        "author": "井上よしひさ",
        "work_key": "潜入!淫縛女捜査官",
        "keep_key": "[中国翻訳] [無修正] [DL版]",
        "note": "保留标准版"
    },
    {
        "author": "越山弱衰",
        "work_key": "艶事に染まる",
        "keep_key": "20250602",
        "note": "保留更新版"
    },
    {
        "author": "chin",
        "work_key": "交尾のマナー",
        "keep_key": "調色",
        "note": "保留調色版"
    },
    {
        "author": "ment",
        "work_key": "ホントの私が見せる顔",
        "keep_key": "ホントの私",
        "note": "保留日文标题版"
    },
    {
        "author": "mogg",
        "work_key": "行列のできる少女",
        "keep_key": "行列のできる少女 [中国翻訳]",
        "note": "保留日文标题版"
    },
    {
        "author": "紺菓",
        "work_key": "My Sweet Honey",
        "keep_key": "My Sweet",
        "note": "保留英文标题版"
    },
    {
        "author": "DISTANCE",
        "work_key": "じょしラク",
        "keep_key": "EagleHawk",
        "note": "保留EagleHawk漢化版"
    },
    {
        "author": "Danimaru",
        "work_key": "もう一度、してみたい",
        "keep_key": "[無修正]",
        "note": "保留無修正版"
    },
    {
        "author": "Cuvie",
        "work_key": "いっぱい揺らして",
        "keep_key": "[中国翻訳] [美少女之友去水印]",
        "note": "保留人类翻译版(删除Sakura AI版)"
    },
    {
        "author": "Akatsuki Myuuto",
        "work_key": "異世界ハーレム",
        "keep_key": "ハーレムパラダイス♡上",
        "note": "保留日文标题版"
    },
    {
        "author": "Borushichi",
        "work_key": "女の子には勝てナイ感じ",
        "keep_key": "特装版",
        "note": "保留特装版"
    },
    {
        "author": "Iwami Yasoya",
        "work_key": "オホ声の響く街",
        "keep_key": "オホ声の響く街 [中国翻訳]",
        "note": "保留日文标题版"
    },
    {
        "author": "SINK",
        "work_key": "母さんはオナホール",
        "keep_key": "[v2]",
        "note": "保留v2版"
    },
    {
        "author": "TANABE",
        "work_key": "たわわめると",
        "keep_key": "[無修正]",
        "note": "保留無修正版"
    },
    {
        "author": "Do well !!! (たつか)",
        "work_key": "本気にしちゃって",
        "keep_key": "特装版",
        "note": "保留特装版"
    },
    {
        "author": "杜若つくね",
        "work_key": "サド★部",
        "keep_key": "[v2]",
        "note": "保留v2版"
    },
    {
        "author": "ウエノ直哉",
        "work_key": "オーガズム",
        "keep_key": "[v2]",
        "note": "保留v2版"
    },
    {
        "author": "干支門三十四",
        "work_key": "少女は絶対犯される",
        "keep_key": "[v2]",
        "note": "保留v2版"
    },
    {
        "author": "鈴月あこに",
        "work_key": "発情季節",
        "keep_key": "[v2]",
        "note": "保留v2版"
    },
    {
        "author": "秋乃秀文",
        "work_key": "媚熱",
        "keep_key": "[v2]",
        "note": "保留v2版"
    },
    {
        "author": "縞浦",
        "work_key": "怪＋インモラル",
        "keep_key": "中国翻訳",
        "note": "保留人类翻译版(删除MTL版)"
    },
    {
        "author": "腐蝕",
        "work_key": "金烏玉兎恋歌",
        "keep_key": "[中国翻訳] [DL版]",
        "note": "保留标准版(删除换源版)"
    },
    {
        "author": "チグチミリ",
        "work_key": "ひとりじゃできないもん",
        "keep_key": "[中国翻訳]",
        "note": "保留带翻译标签版"
    },
    {
        "author": "八月薫",
        "work_key": "巨乳純情剣 紗希",
        "keep_key": "[中国翻訳]",
        "note": "保留简洁版(删除冗长标题版)"
    },
    {
        "author": "土肥泥助",
        "work_key": "少女はダマされ犯されて",
        "keep_key": "[中国翻訳] [DL版]",
        "note": "保留标准版(删除(2)后缀下载重复)"
    },
    {
        "author": "目高健一",
        "work_key": "乳欲児姦",
        "keep_key": "[中国翻訳] [DL版]",
        "note": "保留完整版"
    },
    {
        "author": "玄鉄絢",
        "work_key": "たえちゃんとじみこさん 2",
        "keep_key": "[中国翻訳] [DL版]",
        "note": "保留标准版(删除(2)后缀下载重复)"
    },
]


def list_files(author_dir):
    """列出作者目录下的所有 ZIP 文件"""
    d = os.path.join(BASE, author_dir)
    if not os.path.isdir(d):
        return []
    return sorted([f for f in os.listdir(d) if f.endswith('.zip') and not f.startswith('._')])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path(BASE), help="NAS 漫画根目录")
    parser.add_argument("--execute", action="store_true", help="执行隔离；默认只预览")
    parser.add_argument("--quarantine", type=Path, help="隔离目录；默认位于漫画根目录下")
    return parser.parse_args()


def main() -> int:
    global BASE
    args = parse_args()
    BASE = str(args.base.expanduser().resolve())
    if not os.path.isdir(BASE):
        print(f"❌ 根目录不存在或卷未挂载: {BASE}")
        return 2
    dry_run = not args.execute
    quarantine_root = str(
        (args.quarantine or Path(BASE) / ".codex-dedup-quarantine" / datetime.now().strftime("%Y%m%d-%H%M%S"))
        .expanduser()
        .resolve()
    )
    if dry_run:
        print("=" * 70)
        print("🔍 DRY RUN 模式 — 只检查不删除")
        print("   确认无误后，加 --execute 参数执行实际删除")
        print("=" * 70)

    total_delete = 0
    total_size = 0
    errors = []
    planned_moves = []
    missing_author_rules = 0

    for rule in RULES:
        author = rule["author"]
        work = rule["work_key"]
        keep = rule["keep_key"]
        note = rule.get("note", "")

        author_dir = os.path.join(BASE, author)
        if not os.path.isdir(author_dir):
            missing_author_rules += 1
            continue

        files = list_files(author)
        # 同时检查子目录中的ZIP
        for sub in os.listdir(author_dir):
            subp = os.path.join(author_dir, sub)
            if os.path.isdir(subp) and not sub.startswith('.'):
                for f in os.listdir(subp):
                    if f.endswith('.zip') and not f.startswith('._'):
                        files.append(os.path.join(sub, f))

        # 找到匹配 work_key 的文件
        matches = [f for f in files if work in f]
        if len(matches) <= 1:
            continue  # 没有重复，跳过

        # 找到要保留的
        keep_file = None
        for f in matches:
            if keep in f:
                keep_file = f
                break

        if not keep_file:
            errors.append(f"⚠️ [{author}] {work}: 未找到保留文件 (keep_key='{keep}')")
            for f in matches:
                errors.append(f"   候选: {f}")
            continue

        # 要删除的
        to_delete = [f for f in matches if f != keep_file]

        if to_delete:
            print(f"\n📦 [{author}] {note}")
            print(f"   ✅ 保留: {keep_file}")
            for f in to_delete:
                fpath = os.path.join(author_dir, f)
                try:
                    size_mb = os.path.getsize(fpath) / (1024 * 1024)
                except OSError:
                    size_mb = 0
                total_size += size_mb
                total_delete += 1
                print(f"   🗑️  隔离: {f} ({size_mb:.0f} MB)")
                if not dry_run:
                    relative = os.path.relpath(fpath, BASE)
                    planned_moves.append((fpath, os.path.join(quarantine_root, relative)))

    if not dry_run and planned_moves:
        os.makedirs(quarantine_root, exist_ok=False)
        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "base": BASE,
            "operations": [
                {"source": source, "quarantine": destination}
                for source, destination in planned_moves
            ],
        }
        manifest_path = os.path.join(quarantine_root, "manifest.json")
        with open(manifest_path, "x", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
        for source, destination in planned_moves:
            try:
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                if os.path.exists(destination):
                    raise OSError(f"隔离目标已存在: {destination}")
                shutil.move(source, destination)
                print(f"       ✅ 已移入 {destination}")
            except OSError as exc:
                errors.append(f"       ❌ 隔离失败: {exc}")

    print(f"\n{'=' * 70}")
    print(f"{'🔍 DRY RUN 汇总' if dry_run else '✅ 实际执行汇总'}")
    print(f"   隔离候选数: {total_delete}")
    print(f"   可回收空间: {total_size/1024:.1f} GB")
    if not dry_run and total_delete:
        print(f"   恢复目录: {quarantine_root}")
    if missing_author_rules:
        print(f"   跳过未收录作者规则: {missing_author_rules}")
    if errors:
        print(f"   ⚠️ 问题: {len(errors)}")
        for e in errors[:10]:
            print(f"      {e}")
    print(f"{'=' * 70}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

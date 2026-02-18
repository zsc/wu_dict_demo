#!/usr/bin/env python3
"""
从 `吴语苏州话词典.mdx.txt` 抽取通用吴拼并转写为 IPA。

默认：抽取去重后的 syllable token → IPA（TSV）。
也可输出整行 key → IPA。

示例：
  python scripts/extract_wupin_ipa.py \\
    --input '吴语词典/out/吴语苏州话词典.mdx.txt' \\
    --output out/wupin_syllable_ipa.tsv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Iterable, Iterator, List, Optional, Set, Tuple


# 允许在未安装包的情况下运行（从 repo 根目录执行时生效）
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from wu_pinyin.ipa import wupin_key_to_ipa, wupin_token_to_ipa  # noqa: E402


PINYIN_KEY_RE = re.compile(r"^[a-z]+[0-9a-z\[\] ,]*$")


def iter_mdx_pinyin_keys(file_path: str) -> Iterator[str]:
    """
    迭代提取“拼音键”条目块（见 EXTRACT.md）。
    规则：当前行像拼音键，且下一行以 <p> 开头。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        it = iter(f)
        for line in it:
            key = line.rstrip("\n\r")
            if not key or key == "</>":
                continue
            if not PINYIN_KEY_RE.match(key):
                continue

            # lookahead: 下一行内容行
            content = next(it, "")
            if content.lstrip().startswith("<p>"):
                yield key.strip()


def iter_tokens_from_key(key: str) -> Iterable[str]:
    """将 key 拆成 token（仅用于 syllable 模式的去重抽取）。"""
    raw_tokens = [t for t in re.split(r"[ ,]+", key.strip()) if t]
    merged = []
    for tok in raw_tokens:
        if tok and tok[0].isdigit() and merged:
            merged[-1] = f"{merged[-1]}{tok}"
            continue
        merged.append(tok)
    return merged


def write_tsv(rows: Iterable[Tuple[str, str]], out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("wupin\tipa\n")
        for wupin, ipa in rows:
            f.write(f"{wupin}\t{ipa}\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Extract wupin and convert to IPA")
    parser.add_argument(
        "--input",
        default="吴语词典/out/吴语苏州话词典.mdx.txt",
        help="输入 MDX txt 路径",
    )
    parser.add_argument(
        "--output",
        default="out/wupin_syllable_ipa.tsv",
        help="输出 TSV 路径",
    )
    parser.add_argument(
        "--mode",
        choices=["syllable", "key"],
        default="syllable",
        help="输出粒度：syllable=去重 token；key=去重整行 key",
    )
    parser.add_argument(
        "--tone",
        choices=["none", "base", "sandhi"],
        default="sandhi",
        help="声调输出：none/base/sandhi",
    )
    args = parser.parse_args(argv)

    input_path = args.input
    out_path = Path(args.output)

    if args.mode == "key":
        keys = sorted(set(iter_mdx_pinyin_keys(input_path)))
        rows = ((k, wupin_key_to_ipa(k, tone=args.tone)) for k in keys)
        write_tsv(rows, out_path)
        return 0

    # syllable mode
    tokens: Set[str] = set()
    for key in iter_mdx_pinyin_keys(input_path):
        tokens.update(iter_tokens_from_key(key))

    rows = ((t, wupin_token_to_ipa(t, tone=args.tone)) for t in sorted(tokens))
    write_tsv(rows, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
吴语拼音转换器 CLI
"""

import sys
import json
from pathlib import Path
from typing import List

from .loader import DataLoader
from .converter import WuConverter
from .ipa import wupin_key_to_ipa, wupin_token_to_ipa


def print_usage():
    """打印使用帮助"""
    print("""吴语拼音转换器 (Wu Pinyin Converter)

Usage:
    wu-pinyin [options] <text>
    wu-pinyin [options] -f <file>
    echo <text> | wu-pinyin [options]

Options:
    -h, --help          显示帮助
    -v, --verbose       显示分词详情
    -a, --alternatives  显示多音字备选读音
    -f, --file FILE     从文件读取输入
    -o, --output FILE   输出到文件
    -d, --data-dir DIR  数据文件目录 (默认: ./data)
    --format FORMAT     输出格式: text/json (默认: text)
    --separator SEP     拼音分隔符 (默认: 空格)
    --ipa               输出 IPA（由吴语拼音按规则转写）
    --tone TONE         IPA 声调输出: none/base/sandhi (默认: sandhi)

Examples:
    wu-pinyin "苏州话"
    wu-pinyin -v "苏州话很好"
    wu-pinyin -a "吴"
    wu-pinyin --ipa "苏州话"
    wu-pinyin -f input.txt -o output.txt
    echo "苏州" | wu-pinyin
""")


def _maybe_wupin_key_to_ipa(s: str, tone: str) -> str:
    if not s:
        return s
    if s == "?":
        return "?"
    if not any("a" <= ch <= "z" for ch in s):
        return s
    return wupin_key_to_ipa(s, tone=tone)


def _maybe_wupin_token_to_ipa(s: str, tone: str) -> str:
    if not s:
        return s
    if s == "?":
        return "?"
    if not any("a" <= ch <= "z" for ch in s):
        return s
    return wupin_token_to_ipa(s, tone=tone)


def format_text_output(
    segments,
    show_details: bool = False,
    show_alternatives: bool = False,
    separator: str = " ",
    to_ipa: bool = False,
    ipa_tone: str = "sandhi",
) -> str:
    """格式化文本输出"""
    lines = []
    
    for seg in segments:
        display_pinyin = _maybe_wupin_key_to_ipa(seg.pinyin, ipa_tone) if to_ipa else seg.pinyin
        display_alts = (
            [_maybe_wupin_token_to_ipa(a, ipa_tone) for a in (seg.alternatives or [])]
            if to_ipa
            else (seg.alternatives or [])
        )

        if show_details or show_alternatives:
            if display_alts:
                alt_str = "/".join(display_alts)
                lines.append(f"{seg.text}: {display_pinyin} [{alt_str}]")
            else:
                lines.append(f"{seg.text}: {display_pinyin}")
        else:
            lines.append(display_pinyin)
    
    if show_details or show_alternatives:
        return "\n".join(lines)
    else:
        return separator.join(lines)


def format_json_output(segments, to_ipa: bool = False, ipa_tone: str = "sandhi") -> str:
    """格式化 JSON 输出"""
    data = []
    for seg in segments:
        item = {
            "text": seg.text,
            "pinyin": seg.pinyin,
            "is_word": seg.is_word
        }
        if seg.alternatives:
            item["alternatives"] = seg.alternatives
        if to_ipa:
            item["ipa"] = _maybe_wupin_key_to_ipa(seg.pinyin, ipa_tone)
            if seg.alternatives:
                item["alternatives_ipa"] = [
                    _maybe_wupin_token_to_ipa(a, ipa_tone) for a in seg.alternatives
                ]
        data.append(item)
    
    return json.dumps(data, ensure_ascii=False, indent=2)


def main(args: List[str] = None):
    """CLI 主入口"""
    if args is None:
        args = sys.argv[1:]
    
    # 解析参数
    text = None
    file_path = None
    output_path = None
    data_dir = None
    verbose = False
    alternatives = False
    format_type = "text"
    separator = " "
    to_ipa = False
    ipa_tone = "sandhi"
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ("-h", "--help"):
            print_usage()
            return 0
        
        elif arg in ("-v", "--verbose"):
            verbose = True
        
        elif arg in ("-a", "--alternatives"):
            alternatives = True
        
        elif arg in ("-f", "--file"):
            if i + 1 >= len(args):
                print("Error: --file requires an argument", file=sys.stderr)
                return 1
            file_path = args[i + 1]
            i += 1
        
        elif arg in ("-o", "--output"):
            if i + 1 >= len(args):
                print("Error: --output requires an argument", file=sys.stderr)
                return 1
            output_path = args[i + 1]
            i += 1
        
        elif arg in ("-d", "--data-dir"):
            if i + 1 >= len(args):
                print("Error: --data-dir requires an argument", file=sys.stderr)
                return 1
            data_dir = args[i + 1]
            i += 1
        
        elif arg == "--format":
            if i + 1 >= len(args):
                print("Error: --format requires an argument", file=sys.stderr)
                return 1
            format_type = args[i + 1]
            i += 1
        
        elif arg == "--separator":
            if i + 1 >= len(args):
                print("Error: --separator requires an argument", file=sys.stderr)
                return 1
            separator = args[i + 1]
            i += 1

        elif arg == "--ipa":
            to_ipa = True

        elif arg == "--tone":
            if i + 1 >= len(args):
                print("Error: --tone requires an argument", file=sys.stderr)
                return 1
            ipa_tone = args[i + 1]
            if ipa_tone not in {"none", "base", "sandhi"}:
                print("Error: --tone must be one of none/base/sandhi", file=sys.stderr)
                return 1
            i += 1
        
        elif not arg.startswith("-") and text is None:
            text = arg
        
        else:
            print(f"Error: Unknown option: {arg}", file=sys.stderr)
            return 1
        
        i += 1
    
    # 获取输入文本
    if text is None and file_path is None:
        # 尝试从 stdin 读取
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            print("Error: No input provided", file=sys.stderr)
            return 1
    
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            return 1
    
    # 初始化转换器
    try:
        loader = DataLoader(data_dir)
        converter = WuConverter(loader)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nPlease run the builder first to generate data files:", file=sys.stderr)
        print("  python -m wu_pinyin.builder", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error initializing converter: {e}", file=sys.stderr)
        return 1
    
    # 转换
    try:
        segments = converter.convert(text)
    except Exception as e:
        print(f"Error converting text: {e}", file=sys.stderr)
        return 1
    
    # 格式化输出
    if format_type == "json":
        output = format_json_output(segments, to_ipa=to_ipa, ipa_tone=ipa_tone)
    else:
        output = format_text_output(
            segments,
            verbose,
            alternatives,
            separator=separator,
            to_ipa=to_ipa,
            ipa_tone=ipa_tone,
        )
    
    # 输出
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output)
                f.write('\n')
            print(f"Output written to: {output_path}")
        except Exception as e:
            print(f"Error writing output: {e}", file=sys.stderr)
            return 1
    else:
        print(output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

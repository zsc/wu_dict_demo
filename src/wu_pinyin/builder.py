#!/usr/bin/env python3
"""
Build words.json and char_base.json from MDX dictionary file.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


def normalize_pinyin(pinyin: str) -> str:
    """
    规范化拼音: 去除变调标记和轻声标记
    如: "bu4[23]" → "bu4", "aeq5[51]0" → "aeq5"
    """
    # 去除变调标记 [数字]
    pinyin = re.sub(r'\[\d+\]', '', pinyin)
    # 去除末尾的轻声标记 0
    pinyin = pinyin.rstrip('0')
    return pinyin.strip()


def parse_mdx_txt(file_path: str) -> List[Tuple[str, str, str]]:
    """
    解析 MDX txt 文件，提取 (拼音, 简体汉字, 繁体汉字) 三元组
    
    格式示例:
    aeq7
    <p>aeq7</p><p>揠 （揠）</p><p>阿 （阿）</p>...
    </>
    """
    entries = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n\r')
        
        # 跳过空行和结束标记
        if not line or line == '</>':
            i += 1
            continue
        
        # 检查是否是拼音行（小写字母开头，包含数字，可能有空格）
        if re.match(r'^[a-z]+[0-9a-z\[\] ]*$', line):
            pinyin_key = line.strip()
            
            # 读取下一行内容行
            if i + 1 < len(lines):
                content_line = lines[i + 1].rstrip('\n\r')
                
                # 解析 <p>...</p> 内容
                # 格式: <p>拼音</p><p>繁体 （简体）</p><p>繁体2 （简体2）</p>...
                pattern = r'<p>([^<]*)</p>'
                matches = re.findall(pattern, content_line)
                
                if len(matches) >= 2:
                    # 第一个是重复的拼音键
                    for match in matches[1:]:
                        # 格式: "鴨 （鸭）" 或 "阿媽 （阿妈）" 或 "X （X）"
                        # 可能有空格或其他字符
                        hanzi_match = re.match(r'^(.+?) （(.+?)）$', match.strip())
                        if hanzi_match:
                            traditional = hanzi_match.group(1).strip()
                            simplified = hanzi_match.group(2).strip()
                            
                            # 规范化拼音
                            normalized = normalize_pinyin(pinyin_key)
                            
                            entries.append((normalized, simplified, traditional))
            
            i += 2  # 跳过内容行
        else:
            i += 1
    
    return entries


def build_data_files(input_path: str, output_dir: str):
    """
    生成 words.json 和 char_base.json
    
    - words.json: {简体词语: 拼音}，按长度降序排列，用于 greedy 匹配
    - char_base.json: {简体单字: [拼音列表]}，用于 fallback
    """
    print(f"Parsing {input_path}...")
    entries = parse_mdx_txt(input_path)
    print(f"Found {len(entries)} entries")
    
    words: Dict[str, str] = {}
    char_base: Dict[str, List[str]] = {}
    
    for pinyin, simplified, traditional in entries:
        if not simplified:
            continue
        
        # 过滤掉包含特殊字符的条目
        if any(c in simplified for c in ['□', '[', ']']) or simplified == 'X':
            continue
        
        # 检查是否只包含汉字
        is_all_chinese = all('\u4e00' <= c <= '\u9fff' for c in simplified)
        
        if not is_all_chinese:
            continue
        
        if len(simplified) == 1:
            # 单字条目
            char = simplified
            if char not in char_base:
                char_base[char] = []
            if pinyin and pinyin not in char_base[char]:
                char_base[char].append(pinyin)
        else:
            # 词语条目
            if simplified not in words:
                words[simplified] = pinyin
            # 如果已有，保留较长的拼音（可能是更完整的读音）
            elif len(pinyin) > len(words[simplified]):
                words[simplified] = pinyin
    
    # 对多音字的拼音进行排序（简单的启发式：较短的拼音可能是更常见的）
    for char in char_base:
        char_base[char] = sorted(char_base[char], key=lambda x: (len(x), x))
    
    # words.json: 按词语长度降序，greedy 匹配时需要
    words = dict(sorted(words.items(), key=lambda x: -len(x[0])))
    
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 保存 words.json
    words_path = Path(output_dir) / "words.json"
    with open(words_path, 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)
    print(f"Generated {words_path}: {len(words)} words")
    
    # 保存 char_base.json
    char_path = Path(output_dir) / "char_base.json"
    with open(char_path, 'w', encoding='utf-8') as f:
        json.dump(char_base, f, ensure_ascii=False, indent=2)
    print(f"Generated {char_path}: {len(char_base)} characters")
    
    # 打印一些示例
    print("\nSample words (longest 10):")
    for i, (k, v) in enumerate(list(words.items())[:10]):
        print(f"  {k}: {v}")
    
    print("\nSample words (2-char):")
    two_char_words = [(k, v) for k, v in words.items() if len(k) == 2][:10]
    for k, v in two_char_words:
        print(f"  {k}: {v}")
    
    print("\nSample characters (with multiple readings):")
    multi_reading_chars = [(k, v) for k, v in char_base.items() if len(v) > 1][:10]
    for k, v in multi_reading_chars:
        print(f"  {k}: {v}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        input_file = "吴语词典/out/吴语苏州话词典.mdx.txt"
        output_dir = "data"
    else:
        input_file = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "data"
    
    build_data_files(input_file, output_dir)

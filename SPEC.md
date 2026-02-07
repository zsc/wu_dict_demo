# 吴语拼音转换器 CLI - 技术规格文档

## 项目概述

创建一个 Python CLI 工具，将中文文本转换为吴语拼音（苏州话）。使用吴语词典 MDX 数据作为字典源。

## 数据来源

- **文件**: `吴语词典/吴语苏州话词典.mdx`
- **提取命令**: `mdict_utils -x 吴语词典/吴语苏州话词典.mdx -d ./out`
- **提取后文本文件**: `吴语词典/out/吴语苏州话词典.mdx.txt`

### 原始数据格式

```
{拼音键}
<p>{拼音键}</p><p>{繁体汉字} （{简体汉字}）</p>...
</>
```

**示例条目**:
```
iq7
<p>iq7</p><p>乙 （乙）</p><p>一 （一）</p><p>䭂 （䭂）</p>...
</>

aeq bu4[23]0
<p>aeq bu4[23]0</p><p>阿婆 （阿婆）</p>
</>
```

**拼音格式说明**:
- 声母: b, p, m, f, d, t, n, l, g, k, ng, h, j, ch, ts, sh, s, gh, etc.
- 韵母: a, o, e, i, u, y, iq, eq, aq, oq, etc.
- 声调数字: 1-8, 44, 223, 523, 等 (苏州话有7-8个声调)
- 变调标记: `[数字]` 表示连续变调，如 `aeq5[51]` 表示本调5，变调为51
- 轻声: `0` 表示轻声，如 `ma4[23]0`

---

## 数据文件生成

CLI 工具需要先从 MDX 原始数据生成两个 JSON 数据文件，用于下游查询。

### 生成命令

```bash
# 从 MDX txt 生成 words.json 和 char_base.json
wu-pinyin --build-data --input 吴语词典/out/吴语苏州话词典.mdx.txt --output-dir ./data/
```

### 生成的数据文件

#### 1. `words.json` - 词语字典

用于 **greedy 分词匹配**（最长匹配）。

```json
{
  "苏州": "sou1 tseu1",
  "苏州话": "sou1 tseu1 ghe6",
  "阿婆": "aeq bu4",
  "白蒲枣": "baq bu tsau",
  "白果": "baq kou",
  ...
}
```

**结构说明**:
- Key: 简体词语（2字及以上）
- Value: 空格分隔的拼音串
- 按词语长度降序排列，便于 greedy 匹配

#### 2. `char_base.json` - 单字基础字典

用于 **fallback 单字查询**。

```json
{
  "吴": ["ghou2", "ng2"],
  "一": ["iq7", "iq43", "iq51", "iq440"],
  "苏": ["sou1"],
  "州": ["tseu1"],
  "语": ["nyiu6"],
  ...
}
```

**结构说明**:
- Key: 简体单字
- Value: 拼音列表（多音字按常见程度排序）
- 仅用于未匹配到词语时的单字 fallback

### 数据生成逻辑

```python
def build_data_files(mdx_txt_path: str, output_dir: str):
    """
    从 MDX txt 生成 words.json 和 char_base.json
    
    处理逻辑:
    1. 解析 MDX txt，提取所有 (拼音键, 汉字列表)
    2. 判断条目类型:
       - 单字: 繁简都只有一个字符 → 加入 char_base.json
       - 词语: 多个字符 → 加入 words.json
    3. 繁简转换: 使用括号内的简体形式作为 key
    4. 多音字处理: 单字收集所有可能的拼音
    5. 排序输出:
       - words.json: 按词语长度降序，便于 greedy 匹配
       - char_base.json: 按 Unicode 排序
    """
    
    words = {}      # {简体词语: 拼音}
    char_base = {}  # {简体单字: [拼音列表]}
    
    for entry in parse_mdx_txt(mdx_txt_path):
        pinyin = normalize_pinyin(entry.pinyin)  # 去除变调标记，如 "bu4[23]" → "bu4"
        chars = entry.simplified  # 使用简体形式
        
        if len(chars) == 1:
            # 单字条目
            if chars not in char_base:
                char_base[chars] = []
            if pinyin not in char_base[chars]:
                char_base[chars].append(pinyin)
        else:
            # 词语条目
            words[chars] = pinyin
    
    # words.json: 按长度降序，greedy 匹配时需要
    words = dict(sorted(words.items(), key=lambda x: -len(x[0])))
    
    save_json(f"{output_dir}/words.json", words)
    save_json(f"{output_dir}/char_base.json", char_base)
```

---

## 转换算法

### 核心逻辑: Greedy 分词 + Fallback

```python
def convert_text(text: str, words: dict, char_base: dict) -> list[Segment]:
    """
    将中文文本转换为吴语拼音
    
    算法:
    1. 从文本开头开始
    2. 在 words.json 中 greedy 匹配最长词语
       - 若匹配成功: 记录 (词语, 拼音), 跳过该词语长度
       - 若匹配失败: fallback 到 char_base.json 查单字
    3. 重复直到文本结束
    """
    result = []
    i = 0
    
    while i < len(text):
        matched = False
        
        # Greedy 匹配: 从最长可能开始
        max_len = min(10, len(text) - i)  # 最大10字词
        for l in range(max_len, 1, -1):
            substr = text[i:i+l]
            if substr in words:
                result.append(Segment(
                    text=substr,
                    pinyin=words[substr],
                    is_word=True
                ))
                i += l
                matched = True
                break
        
        if not matched:
            # Fallback 到单字
            char = text[i]
            if char in char_base:
                # 使用第一个拼音（最常见读音）
                pinyin = char_base[char][0]
            else:
                pinyin = "?"  # 未找到
            
            result.append(Segment(
                text=char,
                pinyin=pinyin,
                is_word=False
            ))
            i += 1
    
    return result
```

### 示例流程

输入: `"苏州话很好听"`

```
Step 1: i=0, 剩余="苏州话很好听"
  - 尝试匹配 "苏州话很好听"(10) ~ "苏州话"(3)
  - 匹配到 "苏州话" in words.json → "sou1 tseu1 ghe6"
  - i += 3, result=[("苏州话", "sou1 tseu1 ghe6", True)]

Step 2: i=3, 剩余="很好听"
  - 尝试匹配 "很好听"(4) ~ "很好"(2)
  - 未匹配到词语
  - fallback 查 "很" in char_base.json → "hen6"
  - i += 1, result=[..., ("很", "hen6", False)]

Step 3: i=4, 剩余="好听"
  - 匹配到 "好听" in words.json → "hau5 thin1"
  - i += 2, result=[..., ("好听", "hau5 thin1", True)]

输出: "sou1 tseu1 ghe6 hen6 hau5 thin1"
```

---

## 功能需求

### CLI 接口设计

```bash
# 1. 生成数据文件（首次使用或更新字典时）
wu-pinyin --build-data \
  --input 吴语词典/out/吴语苏州话词典.mdx.txt \
  --output-dir ./data/

# 2. 基础用法: 转拼音
wu-pinyin "苏州话"
# 输出: sou1 tseu1 ghe6

# 3. 显示分词细节
wu-pinyin --verbose "苏州话很好"
# 输出:
# 苏州话: sou1 tseu1 ghe6
# 很: hen6
# 好: hau5

# 4. 显示多音字备选
wu-pinyin --alternatives "苏州"
# 输出:
# 苏州: sou1 tseu1
#   苏: sou1
#   州: tseu1

# 5. 单字查询
wu-pinyin --char "吴"
# 输出: ghou2 ng2

# 6. 文件批量转换
wu-pinyin --file input.txt --output output.txt

# 7. JSON 格式输出
wu-pinyin --format json "苏州"
# 输出: [{"text":"苏州","pinyin":"sou1 tseu1","is_word":true}]
```

### 命令行参数

| 参数 | 长参数 | 说明 |
|------|--------|------|
| | `--build-data` | 生成 words.json 和 char_base.json |
| `-i` | `--input` | MDX txt 文件路径（配合 --build-data） |
| `-d` | `--data-dir` | 数据文件目录（默认 ./data/） |
| `-v` | `--verbose` | 显示分词细节 |
| `-a` | `--alternatives` | 显示多音字备选 |
| `-c` | `--char` | 单字查询模式 |
| `-f` | `--file` | 从文件读取输入 |
| `-o` | `--output` | 输出到文件 |
| | `--format` | 输出格式: text/json |
| `-h` | `--help` | 帮助信息 |

---

## 技术架构

### 项目结构

```
wu_pinyin_cli/
├── pyproject.toml
├── README.md
├── SPEC.md
├── src/
│   └── wu_pinyin/
│       ├── __init__.py
│       ├── cli.py           # CLI 入口
│       ├── builder.py       # 数据文件生成器
│       ├── converter.py     # 转换器（greedy + fallback）
│       ├── loader.py        # 加载 words.json / char_base.json
│       └── models.py        # 数据模型
├── data/
│   ├── words.json           # 词语字典（greedy匹配用）
│   └── char_base.json       # 单字字典（fallback用）
└── tests/
    └── test_*.py
```

### 数据模型

```python
from dataclasses import dataclass
from typing import Dict, List

# 运行时加载的数据结构
WordsDict = Dict[str, str]        # words.json: {词语: 拼音}
CharBaseDict = Dict[str, List[str]]  # char_base.json: {单字: [拼音列表]}

@dataclass
class Segment:
    """分词片段结果"""
    text: str
    pinyin: str
    is_word: bool  # True=来自words.json, False=来自char_base.json
```

### 核心模块

#### 1. builder.py - 数据生成器

```python
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

def parse_mdx_entry(line: str) -> Tuple[str, str]:
    """
    解析 MDX txt 中的一行
    返回: (拼音, 简体汉字)
    
    示例:
    '<p>aeq7</p><p>鴨 （鸭）</p>' → ('aeq7', '鸭')
    '<p>aeq bu4[23]0</p><p>阿婆 （阿婆）</p>' → ('aeq bu4', '阿婆')
    """
    
def normalize_pinyin(pinyin: str) -> str:
    """
    规范化拼音: 去除变调标记
    如: "bu4[23]" → "bu4", "aeq5[51]0" → "aeq5"
    """
    return re.sub(r'\[\d+\]', '', pinyin).rstrip('0')

def build_data_files(input_path: str, output_dir: str):
    """
    生成 words.json 和 char_base.json
    """
    words: Dict[str, str] = {}
    char_base: Dict[str, List[str]] = {}
    
    # 解析 MDX...
    # 分类存储...
    
    # words 按长度降序
    words = dict(sorted(words.items(), key=lambda x: -len(x[0])))
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    with open(f"{output_dir}/words.json", 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)
    
    with open(f"{output_dir}/char_base.json", 'w', encoding='utf-8') as f:
        json.dump(char_base, f, ensure_ascii=False, indent=2)
```

#### 2. loader.py - 数据加载器

```python
import json
from pathlib import Path

class DataLoader:
    """加载 words.json 和 char_base.json"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.words: WordsDict = {}
        self.char_base: CharBaseDict = {}
        
    def load(self):
        """加载数据文件"""
        with open(self.data_dir / "words.json", encoding='utf-8') as f:
            self.words = json.load(f)
        
        with open(self.data_dir / "char_base.json", encoding='utf-8') as f:
            self.char_base = json.load(f)
            
    def get_word_pinyin(self, word: str) -> str | None:
        """查询词语拼音"""
        return self.words.get(word)
    
    def get_char_pinyin(self, char: str) -> str | None:
        """查询单字拼音（返回最常见读音）"""
        pinyins = self.char_base.get(char)
        return pinyins[0] if pinyins else None
    
    def get_char_alternatives(self, char: str) -> list[str]:
        """查询单字所有读音"""
        return self.char_base.get(char, [])
```

#### 3. converter.py - 转换器

```python
from typing import List

class WuConverter:
    """吴语拼音转换器 - Greedy + Fallback"""
    
    MAX_WORD_LEN = 10  # 最大词语长度
    
    def __init__(self, loader: DataLoader):
        self.loader = loader
        
    def convert(self, text: str) -> List[Segment]:
        """
        转换文本为吴语拼音
        
        算法: Greedy 分词 + Fallback 到单字
        """
        result = []
        i = 0
        
        while i < len(text):
            # Greedy 匹配最长词语
            matched = False
            max_len = min(self.MAX_WORD_LEN, len(text) - i)
            
            for l in range(max_len, 1, -1):
                substr = text[i:i+l]
                pinyin = self.loader.get_word_pinyin(substr)
                if pinyin:
                    result.append(Segment(text=substr, pinyin=pinyin, is_word=True))
                    i += l
                    matched = True
                    break
            
            if not matched:
                # Fallback 到单字
                char = text[i]
                pinyin = self.loader.get_char_pinyin(char) or "?"
                result.append(Segment(text=char, pinyin=pinyin, is_word=False))
                i += 1
        
        return result
    
    def convert_to_string(self, text: str) -> str:
        """转换为拼音字符串"""
        segments = self.convert(text)
        return " ".join(s.pinyin for s in segments)
```

#### 4. cli.py - 命令行接口

```python
import click
from pathlib import Path

@click.group()
def cli():
    """吴语拼音转换器"""
    pass

@cli.command()
@click.option('-i', '--input', required=True, help='MDX txt 文件路径')
@click.option('-o', '--output-dir', default='./data', help='输出目录')
def build_data(input, output_dir):
    """生成 words.json 和 char_base.json"""
    from .builder import build_data_files
    build_data_files(input, output_dir)
    click.echo(f"数据文件已生成到: {output_dir}")

@cli.command()
@click.argument('text', required=False)
@click.option('-f', '--file', type=click.Path(), help='输入文件')
@click.option('-d', '--data-dir', default='./data', help='数据目录')
@click.option('-v', '--verbose', is_flag=True, help='显示分词细节')
@click.option('-a', '--alternatives', is_flag=True, help='显示多音字备选')
@click.option('--format', type=click.Choice(['text', 'json']), default='text')
def convert(text, file, data_dir, verbose, alternatives, format):
    """转换文本为吴语拼音"""
    # 加载数据
    loader = DataLoader(data_dir)
    loader.load()
    converter = WuConverter(loader)
    
    # 获取输入文本...
    # 转换并输出...
```

---

## 实现步骤

### Phase 1: 数据生成器
1. 解析 MDX txt 文件
2. 实现繁简提取和拼音规范化
3. 生成 words.json（按长度降序）和 char_base.json

### Phase 2: 转换器核心
1. 实现 DataLoader 加载 JSON 数据
2. 实现 Greedy 分词算法
3. 实现 Fallback 到单字逻辑

### Phase 3: CLI 界面
1. `build-data` 子命令生成数据文件
2. `convert` 子命令进行转换
3. 添加 verbose、alternatives 等选项

### Phase 4: 优化
1. 使用 Trie 树优化词语查找（可选）
2. 多音字简单规则消歧

---

## 依赖项

```toml
[project]
name = "wu-pinyin"
version = "0.1.0"
dependencies = [
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]

[project.scripts]
wu-pinyin = "wu_pinyin.cli:cli"
```

---

## 示例输出

```bash
# 生成数据
$ wu-pinyin build-data -i 吴语词典/out/吴语苏州话词典.mdx.txt -o ./data/
生成 words.json: 18,234 个词语
生成 char_base.json: 8,567 个单字

# 转换
$ wu-pinyin convert "苏州话"
sou1 tseu1 ghe6

$ wu-pinyin convert -v "苏州"
苏州: sou1 tseu1 (matched)

$ wu-pinyin convert -v "吴语词典"
吴语: ng nyiu6 (matched)
词典: zy zy (fallback: 词+典)
  词: zy
  典: ty

$ wu-pinyin convert --alternatives "吴"
吴: ng2 (备选: ghou2)
```

---

## 注意事项

1. **Greedy 匹配**: words.json 必须按长度降序排列，确保最长匹配优先
2. **繁简处理**: 输入文本应为简体，与 char_base.json 的 key 一致
3. **多音字**: 单字取 char_base.json 的第一个拼音作为默认读音
4. **缺失字**: 字典中未收录的字输出 `?` 或保留原字
5. **数据更新**: MDX 源文件更新后，需要重新运行 `build-data`

---

## 参考资料

- 提取的词典文件: `吴语词典/out/吴语苏州话词典.mdx.txt`
- 总条目数: 约 25,337 条
- 包含: 单字、词语、俗语、专有名词

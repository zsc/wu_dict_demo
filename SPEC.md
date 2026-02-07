# 吴语拼音转换器 CLI - 技术规格文档

## 项目概述

创建一个 Python CLI 工具，将中文文本转换为吴语拼音（苏州话）。使用吴语词典 MDX 数据作为字典源。

## 数据来源

- **文件**: `吴语词典/吴语苏州话词典.mdx`
- **提取命令**: `mdict_utils -x 吴语苏州话词典.mdx -d ./out`
- **提取后文本文件**: `吴语词典/out/吴语苏州话词典.mdx.txt`

### 数据格式分析

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

ghou2
<p>ghou2</p><p>湖 （湖）</p><p>和 （和）</p><p>吳 （吴）</p>...
</>

aeq7
<p>aeq7</p><p>揠 （揠）</p><p>阿 （阿）</p><p>鴨 （鸭）</p>...
</>
```

**拼音格式说明**:
- 声母: b, p, m, f, d, t, n, l, g, k, ng, h, j, ch, ts, sh, s, gh, etc.
- 韵母: a, o, e, i, u, y, iq, eq, aq, oq, etc.
- 声调数字: 1-8, 44, 223, 523, 等 (苏州话有7-8个声调)
- 变调标记: `[数字]` 表示连续变调，如 `aeq5[51]` 表示本调5，变调为51
- 轻声: `0` 表示轻声，如 `aeq ma4[23]0` 中 `ma` 读轻声

## 功能需求

### 核心功能

1. **单字查询**: 输入单个汉字，返回所有可能的吴语拼音
2. **词语查询**: 输入词语，返回整个词语的吴语拼音
3. **文本转换**: 输入长文本，逐字/逐词转换为吴语拼音
4. **拼音标注模式**: 在汉字上方或旁边标注拼音

### CLI 接口设计

```bash
# 基础用法
wu-pinyin "苏州"
# 输出: sou1 tseu1

# 单字查询（显示所有读音）
wu-pinyin -c "吴"
# 输出:
# 吴:
#   - ghou2
#   - ng2

# 详细模式（带解释）
wu-pinyin -v "苏州"
# 输出:
# 苏州: sou1 tseu1
#   苏: sou1
#   州: tseu1

# 文件输入
wu-pinyin -f input.txt -o output.txt

# 输出格式选择
wu-pinyin --format=csv "苏州话"
# 输出: 苏州话,sou1 zeu1 ghe6

wu-pinyin --format=json "苏州话"
# 输出: [{"char": "苏", "pinyin": "sou1"}, ...]

# 标注模式（HTML 输出）
wu-pinyin --annotate "苏州" --html
# 输出: <ruby>苏<rt>sou1</rt></ruby><ruby>州<rt>tseu1</rt></ruby>

# 显示声调曲线
wu-pinyin --tone-curve "苏州"
# 输出: sou¹ tseu¹ (显示声调曲线/数值)
```

### 命令行参数

| 参数 | 长参数 | 说明 | 示例 |
|------|--------|------|------|
| `-c` | `--char` | 单字模式，显示所有读音 | `-c "一"` |
| `-v` | `--verbose` | 详细输出 | `-v "苏州"` |
| `-f` | `--file` | 从文件读取输入 | `-f input.txt` |
| `-o` | `--output` | 输出到文件 | `-o output.txt` |
| | `--format` | 输出格式: text/csv/json/html | `--format=json` |
| | `--annotate` | 标注模式 | `--annotate` |
| | `--tone-curve` | 显示声调曲线 | `--tone-curve` |
| `-h` | `--help` | 帮助信息 | |
| | `--rebuild` | 重新构建字典索引 | `--rebuild` |

## 技术架构

### 项目结构

```
wu_pinyin_cli/
├── pyproject.toml          # 项目配置
├── README.md               # 用户文档
├── src/
│   └── wu_pinyin/
│       ├── __init__.py
│       ├── cli.py           # CLI 入口
│       ├── converter.py     # 核心转换逻辑
│       ├── dictionary.py    # 字典加载与查询
│       ├── parser.py        # MDX 解析器
│       ├── models.py        # 数据模型
│       └── utils.py         # 工具函数
├── data/
│   └── wu_dict.json         # 编译后的字典缓存
└── tests/
    └── test_*.py
```

### 数据模型

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class PinyinEntry:
    """拼音条目"""
    pinyin: str              # 原始拼音，如 "sou1"
    base_tone: int          # 本调
    sandhi_tone: Optional[str]  # 变调
    is_light: bool          # 是否轻声

@dataclass
class DictEntry:
    """字典条目"""
    traditional: str        # 繁体
    simplified: str         # 简体
    pinyins: List[PinyinEntry]  # 所有读音

@dataclass
class Segment:
    """分词片段"""
    text: str
    pinyin: str
    is_word: bool          # 是否词典中有这个词
```

### 核心模块

#### 1. parser.py - MDX 解析器

```python
import re
from typing import Dict, List

def parse_mdx_txt(file_path: str) -> Dict[str, List[DictEntry]]:
    """
    解析 MDX 提取的 txt 文件
    
    返回: {简体汉字: [{繁体, 拼音列表}, ...]}
    """
    pattern = re.compile(
        r'^(?P<pinyin>[a-z]+[0-9\[\]]*)$\n'
        r'<p>\1</p>'
        r'(?P<entries>(?:<p>[^<]+</p>)*)'
        r'\n</>',
        re.MULTILINE
    )
    # 解析逻辑...
    
def parse_pinyin_tone(pinyin: str) -> PinyinEntry:
    """
    解析拼音中的声调信息
    如: "aeq5[51]" -> base_tone=5, sandhi_tone="51"
        "ma4[23]0" -> base_tone=4, sandhi_tone="23", is_light=True
    """
```

#### 2. dictionary.py - 字典管理

```python
import json
import pickle
from pathlib import Path

class WuDictionary:
    """吴语词典"""
    
    CACHE_FILE = Path(__file__).parent / "data" / "wu_dict.pkl"
    
    def __init__(self):
        self.char_dict: Dict[str, List[DictEntry]] = {}  # 单字字典
        self.word_dict: Dict[str, List[DictEntry]] = {}  # 词语字典
        
    def load_from_mdx(self, mdx_txt_path: str):
        """从 MDX 文本文件加载"""
        
    def build_index(self):
        """构建高效查询索引"""
        
    def save_cache(self):
        """保存为缓存文件"""
        
    def load_cache(self) -> bool:
        """从缓存加载"""
        
    def lookup_char(self, char: str) -> List[DictEntry]:
        """查询单字"""
        
    def lookup_word(self, word: str) -> List[DictEntry]:
        """查询词语"""
```

#### 3. converter.py - 转换器

```python
from typing import List
import jieba  # 或自定义分词

class WuConverter:
    """吴语拼音转换器"""
    
    def __init__(self, dictionary: WuDictionary):
        self.dict = dictionary
        
    def convert(self, text: str, mode: str = "word") -> List[Segment]:
        """
        转换文本为吴语拼音
        
        mode: 
            - "word": 优先整词匹配
            - "char": 逐字转换
        """
        
    def segment(self, text: str) -> List[str]:
        """分词，优先匹配词典中的词语"""
        
    def get_default_pinyin(self, char: str) -> str:
        """获取单字的默认读音（最常见读音）"""
```

#### 4. cli.py - 命令行接口

```python
import click  # 或 argparse

@click.command()
@click.argument('text', required=False)
@click.option('-c', '--char', is_flag=True, help='单字模式')
@click.option('-v', '--verbose', is_flag=True, help='详细输出')
@click.option('-f', '--file', type=click.Path(), help='输入文件')
@click.option('-o', '--output', type=click.Path(), help='输出文件')
@click.option('--format', type=click.Choice(['text', 'csv', 'json', 'html']), 
              default='text', help='输出格式')
@click.option('--annotate', is_flag=True, help='标注模式')
def main(text, char, verbose, file, output, format, annotate):
    """吴语拼音转换器"""
    # 实现...
```

## 实现步骤

### Phase 1: 数据解析
1. 编写 MDX txt 解析器，提取汉字-拼音映射
2. 处理多音字、繁简转换
3. 构建字典索引并缓存

### Phase 2: 核心功能
1. 实现单字查询
2. 实现分词和整词匹配
3. 实现文本转换

### Phase 3: CLI 界面
1. 使用 click 构建 CLI
2. 实现各种输出格式
3. 添加文件 I/O 支持

### Phase 4: 优化
1. 分词算法优化（最大匹配）
2. 多音字消歧（简单规则）
3. 性能优化

## 依赖项

```toml
[project]
name = "wu-pinyin"
version = "0.1.0"
dependencies = [
    "click>=8.0",
    "jieba>=0.42",  # 分词，可选
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "black",
    "ruff",
]

[project.scripts]
wu-pinyin = "wu_pinyin.cli:main"
```

## 示例输出

```bash
$ wu-pinyin "苏州话"
sou1 tseu1 ghe6

$ wu-pinyin -c "一"
一 (iq7/iq43/iq51/iq440)

$ wu-pinyin -v "苏州"
苏: sou1
州: tseu1
=> sou1 tseu1

$ wu-pinyin --format=json "吴语"
[
  {"char": "吴", "pinyin": "ng2", "alternatives": ["ghou2"]},
  {"char": "语", "pinyin": "nyiu6"}
]
```

## 注意事项

1. **多音字**: 苏州话有大量多音字，需要显示所有可能的读音
2. **变调**: 苏州话有复杂的连续变调规则，可先显示单字本调
3. **繁简**: 字典使用繁体，需要处理简体输入
4. **缺失字**: 对于字典中没有的字，给出提示而非报错

## 参考资料

- 提取的词典文件: `吴语词典/out/吴语苏州话词典.mdx.txt`
- 总条目数: 约 25,337 条
- 包含: 单字、词语、俗语、专有名词

# 吴语拼音转换器 (Wu Pinyin Converter)

将中文文本转换为吴语拼音（苏州话）。

## 特点

- **Greedy 分词 + Fallback**: 优先匹配最长词语，失败则回退到单字
- **数据驱动**: 基于吴语苏州话词典 MDX 数据生成
- **多音字支持**: 显示单字的所有备选读音
- **IPA 输出**: 将吴语拼音按规则转写为 IPA
- **轻量快速**: 纯 Python 实现，无需额外依赖

## 安装

```bash
# 开发模式安装
pip install -e .

# 或者直接使用 PYTHONPATH
PYTHONPATH=src python3 -m wu_pinyin "苏州话"
```

## 使用方法

### 基本用法

```bash
# 转换文本
wu-pinyin "苏州话"
# 输出: sou1 tseu1 gho6

# 输出 IPA
wu-pinyin --ipa "苏州话"
# 输出: səu44 ʦøʏ44 ɦo231

# 显示分词详情
wu-pinyin -v "苏州话很好"
# 输出:
# 苏: sou1
# 州: tseu1
# 话: gho6
# 很: hen3
# 好: hau3

# 显示多音字备选
wu-pinyin -a "吴"
# 输出: 吴: ng2 [ng2/ghou2]

# JSON 格式输出
wu-pinyin --format json "苏州"
# 输出: [{"text": "苏", "pinyin": "sou1", "is_word": false}, ...]

# JSON + IPA 字段
wu-pinyin --format json --ipa "吴"
# 输出: [{"text": "吴", "pinyin": "ng2", "ipa": "ŋ223", ...}, ...]
```

### 文件处理

```bash
# 从文件读取
wu-pinyin -f input.txt

# 输出到文件
wu-pinyin -f input.txt -o output.txt

# 管道输入
echo "苏州" | wu-pinyin
```

## 数据文件

- `data/words.json`: 8,193 个词语，按长度降序排列，用于 greedy 匹配
- `data/char_base.json`: 5,858 个单字，用于 fallback 查询

## 重新生成数据

如果需要从原始 MDX 词典重新生成数据文件：

```bash
# 先提取 MDX 文件
mdict_utils -x 吴语词典/吴语苏州话词典.mdx -d ./out

# 然后生成数据文件
python -m wu_pinyin.builder 吴语词典/out/吴语苏州话词典.mdx.txt data/
```

## 项目结构

```
.
├── data/
│   ├── words.json          # 词语字典（greedy 匹配用）
│   └── char_base.json      # 单字字典（fallback 用）
├── src/wu_pinyin/
│   ├── __init__.py
│   ├── __main__.py         # 模块入口
│   ├── cli.py              # 命令行接口
│   ├── loader.py           # 数据加载器
│   ├── converter.py        # 转换器核心
│   └── builder.py          # 数据生成器
├── pyproject.toml
└── README.md
```

## 转换算法

1. 从文本开头开始，使用 greedy 策略在 words.json 中匹配最长词语
2. 如果匹配成功，记录词语拼音，跳过该词语长度
3. 如果匹配失败（未找到词语），fall back 到 char_base.json 查单字
4. 重复直到文本结束

## License

MIT

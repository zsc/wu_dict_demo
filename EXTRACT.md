# EXTRACT SPEC（从 `吴语苏州话词典.mdx.txt` 抽取通用吴拼并转 IPA）

## 目标

实现一个 Python 脚本：

1. 从 `吴语词典/out/吴语苏州话词典.mdx.txt` 中抽取“通用吴拼”（下文简称 *wupin*）
2. 将抽取出的 wupin 转成 IPA（含/不含声调可配置）
3. 输出可复用的数据文件（默认 TSV）

本仓库现有的 `src/wu_pinyin/builder.py` 能解析 MDX txt 并生成 `words.json/char_base.json`；本任务新增的是 **“抽取 + wupin→IPA”** 的工具链。

---

## 输入数据（`吴语苏州话词典.mdx.txt`）结构

`mdict_utils -x` 导出的 txt 混合了两类内容：

### A. “拼音键”条目块（本任务的主要抽取对象）

典型结构：

```text
aeq7
<p>aeq7</p><p>揠 （揠）</p><p>阿 （阿）</p>...
</>
```

特征：
- 第一行是 *wupin key*（可包含空格/逗号，表示多音节短语或带标点）
- 第二行通常以 `<p>` 开头，第一段 `<p>` 里会重复 wupin key
- 以单独一行 `</>` 结束

### B. “汉字键”HTML 条目块（可选：用于抽取现成 IPA 对照以做校验/补全）

典型结构（同一条目可能出现多组 `text-primary`/`text-success`）：

```html
<h3>乎 <small class="text-primary">ghou2</small>
<small class="text-success">[ɦəu223]</small> <a href="sound://ghou2.wav"> 发音 </a>
```

特征：
- `text-primary` 中是 wupin（常见为单音节+声调）
- `text-success` 中是 IPA（方括号内，末尾常带 5 度标记数字如 `223/231/44/51/523/23`）
- 并非所有条目都带 `text-success`（即缺 IPA）

---

## 抽取规则

### 1) 抽取 wupin key（条目块 A）

判定逻辑（流式逐行）：
- 行满足正则：`^[a-z]+[0-9a-z\\[\\] ,]*$`
- 且其下一行以 `<p>` 开头（用于排除 HTML 块里的杂项）

抽取结果两种粒度（脚本可选）：
- `key` 粒度：整行 key（可能多音节/含逗号）
- `syllable` 粒度：将 key 以空白与 `,` 切分后的“音节 token”（默认输出）

### 2) wupin token 归一化（用于查表/转写）

对每个 token：
- 去掉变调标记：移除所有 `[\d+]`（如 `gen5[51]0 → gen50`）
- 去掉轻声标记：去掉末尾 `0`（如 `bu40 → bu4`）
- 记录：
  - `base_tone`: token 末尾的数字（可能是 `1-8` 或 `44/223/...`），若不存在则为空
  - `sandhi_tone`: 若原 token 含 `[\d+]`，取括号内数字作为“实现调值”

> 注意：真实语流声调可能以 `sandhi_tone` 为准；也可能只需要 citation tone（`base_tone`）。脚本提供选项控制。

---

## wupin → IPA 转写规范

### 输出形式

- 每个 token 输出为 `ipa_body + tone_digits`（tone 可选）
  - 示例：`ghou2 → ɦəu223`
  - 示例：`aeq7 → aʔ43`
- 多音节 key：逐 token 转写，保留原分隔符（空格、逗号）

### 声母（onset）映射（核心集合）

以最长匹配优先（如 `tsh` 优先于 `ts`）：

| wupin | IPA |
|---|---|
| p / ph / b | p / pʰ / b |
| t / th / d | t / tʰ / d |
| k / kh / g | k / kʰ / g |
| f / v | f / v |
| m / n / ng | m / n / ŋ |
| ts / tsh | ʦ / ʦʰ |
| c / ch / j | ʨ / ʨʰ / ʥ |
| s / z | s / z |
| sh | ɕ |
| gn | ȵ |
| h / gh | x / ɦ |

补充：少量条目出现 `dz / fh / pp / cn` 等非常规串，脚本允许保守处理（输出 `?` 或原样），不作为主覆盖目标。

### 韵母（rime）映射（以“苏州话拼音教程”口径为主）

**基本元音**
- `a → ɑ`
- `e → ᴇ`（小型大写 E）
- `i → i`
- `o → o`
- `u → u`
- `y → ɿ`（舌尖元音）

**组合元音**
- `au → æ`
- `eu → øʏ`
- `ie → iɪ`
- `iu → y`
- `oe → ø`
- `ou → əu`
- `ieu → iʏ`

**鼻音韵**
- `an → ã`
- `aon / oan → ɑ̃`
- `en → ən`
- `in → in`
- `on → oŋ`
- `iun → yn`

**入声（喉塞尾）**
- `aeq / aeh → aʔ`
- `aq / ah → ɑʔ`
- `eq / eh → əʔ`
- `iq / ih → iəʔ`
- `oq / oh → oʔ`

**介音组合（递归拼接）**
- `i + (a/au/an/aq/aeq/...)`：如 `ian → iã`，`iaq → iɑʔ`，`iaeq → iaʔ`
- `u + (e/en/eq/aeq/aon/...)`：如 `ue → uᴇ`，`uen → uən`，`ueq → uəʔ`，`uaon → uɑ̃`
- 其他如 `ioe → iø`，`ioq → ioʔ`，`ion → ioŋ`，`uoe → uø`

**自成音节**
- 当 rime 为空（如 `ng2`）：用声母自身作音节核（`ŋ223`）

### `y- / w-` 起首音节（零声母系列）

该词典中大量零声母音节写作 `y...` / `w...`，其 IPA 常带 **[ɦ]** 起始（见词典内置 IPA 示例，如 `we6 → ɦuᴇ231`、`yan6 → ɦiã231`）。

规范：
- `wX` 系列：输出前缀 `ɦu` + 转写 `X`
  - `we → ɦuᴇ`
  - `wen → ɦuən`
  - `woe → ɦuø`
  - `waon → ɦuɑ̃`
- `yX` 系列：
  - 若为 `yu...`：前缀 `ɦ` + 以 `y`（前圆唇高元音）为核（如 `yu2 → ɦy223`）
  - 否则：前缀 `ɦi` + 转写 `X`（如 `yan6 → ɦiã231`，`yeu6 → ɦiʏ231`，`yoe2 → ɦiø223`）

---

## 声调处理

脚本提供 `--tone {none,base,sandhi}`：
- `none`：不输出调值
- `base`：使用 token 的末尾数字（去掉 `[\d+]` 与末尾 `0` 后）
- `sandhi`：若存在 `[\d+]`，优先使用括号内数字；否则回退到 `base`

调值规范：
- 若 tone 已是 5 度数字（如 `44/223/231/51/523/23`），直接附加
- 若为类别数字 `1-8`，映射到调值（从词典内置 IPA 统计归纳）：
  - `1 → 44`
  - `2 → 223`
  - `3 → 51`
  - `5 → 523`
  - `6 → 231`
  - `7 → 43`
  - `8 → 23`
  - `4`：数据不足，暂保留原值 `4`（不展开）

---

## 输出文件

默认输出 TSV（UTF-8）：
- `wupin`：原 token（去括号/轻声前的原样或规范化后可选）
- `ipa`：转写结果（不加 `[]`）

可选输出：
- `--mode key`：输出整行 key → IPA（保留空格与逗号）
- `--mode syllable`：输出去重后的 token → IPA（默认）

---

## 成功判定

- 能在本仓库下直接运行脚本，对 `吴语词典/out/吴语苏州话词典.mdx.txt` 生成输出文件
- 对常见样例可得到合理结果：
  - `ghou2 → ɦəu223`
  - `aeq7 → aʔ43`
  - `iq7 → iəʔ43`
  - `we6 → ɦuᴇ231`
  - `yan6 → ɦiã231`


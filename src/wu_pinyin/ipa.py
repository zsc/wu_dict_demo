#!/usr/bin/env python3
"""
通用吴拼（苏州话）→ IPA 转写工具。

该模块按本仓库 EXTRACT.md 的约定实现：
- 解析 token 中的变调标记 [..]、轻声 0、声调数字
- 将 wupin 音节转写为 IPA（默认附加 5 度调值数字）
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional, Tuple


_BRACKET_TONE_RE = re.compile(r"\[(\d+)\]")
_TRAILING_DIGITS_RE = re.compile(r"(\d+)$")


TONE_CATEGORY_TO_CHAO = {
    # 从词典内置 IPA（text-success）统计归纳的主流映射
    "1": "44",
    "2": "223",
    "3": "51",
    # "4": 未充分覆盖，保留原值
    "5": "523",
    "6": "231",
    "7": "43",
    "8": "23",
}


ONSET_TO_IPA = {
    "tsh": "ʦʰ",
    "ts": "ʦ",
    "th": "tʰ",
    "t": "t",
    "ph": "pʰ",
    "p": "p",
    "b": "b",
    "m": "m",
    "f": "f",
    "v": "v",
    "d": "d",
    "n": "n",
    "l": "l",
    "kh": "kʰ",
    "k": "k",
    "g": "g",
    "ng": "ŋ",
    "h": "x",
    "gh": "ɦ",
    "ch": "ʨʰ",
    "c": "ʨ",
    "j": "ʥ",
    "sh": "ɕ",
    "gn": "ȵ",
    "s": "s",
    "z": "z",
    # w- 系列（零声母）：约定为 ɦu + rime
    "w": "ɦu",
    # 低频/非标准串：尽量给出保守映射
    "dz": "dz",
    # fh/pp/cn 在词典中极少，且并不总是标准 IPA；保守输出原样
    "fh": "fh",
    "pp": "pp",
    "cn": "cn",
}


RIME_ATOMIC_TO_IPA = {
    # 基本元音
    "a": "ɑ",
    "e": "ᴇ",
    "i": "i",
    "o": "o",
    "u": "u",
    "y": "ɿ",
    # 组合元音
    "au": "æ",
    "eu": "øʏ",
    "ie": "iɪ",
    "iu": "y",
    "oe": "ø",
    "ou": "əu",
    "yu": "ʮ",
    "ieu": "iʏ",
    # 鼻音韵
    "an": "ã",
    "aon": "ɑ̃",
    "oan": "ɑ̃",
    "en": "ən",
    "in": "in",
    "on": "oŋ",
    "iun": "yn",
    # 自成音节/特殊
    "er": "əl",
}


# 入声：q/h 记号等价，统一在这里显式列出
CHECKED_RIME_TO_IPA = {
    "aeq": "aʔ",
    "aeh": "aʔ",
    "aq": "ɑʔ",
    "ah": "ɑʔ",
    "eq": "əʔ",
    "eh": "əʔ",
    "iq": "iəʔ",
    "ih": "iəʔ",
    "oq": "oʔ",
    "oh": "oʔ",
    # iuq / iueh：在词典内置 IPA 中常对应 yəʔ
    "iuq": "yəʔ",
    "iueh": "yəʔ",
    # y 系列（极少）：保守处理
    "yh": "ɿʔ",
    "yq": "ɿʔ",
}


_ONSETS_LONGEST_FIRST = sorted(ONSET_TO_IPA.keys(), key=len, reverse=True)


@dataclass(frozen=True)
class ParsedToken:
    raw: str
    body: str
    base_tone: str
    sandhi_tone: str
    neutral: bool


def parse_wupin_token(token: str) -> ParsedToken:
    """
    解析单个 wupin token：
    - 变调: [...], 取最后一个括号内数字为 sandhi_tone
    - 轻声: 末尾 0
    - base_tone: 去括号/去轻声后，末尾连续数字
    """
    raw = token.strip()
    if not raw:
        return ParsedToken(raw=token, body="", base_tone="", sandhi_tone="", neutral=False)

    bracket_tones = _BRACKET_TONE_RE.findall(raw)
    sandhi_tone = bracket_tones[-1] if bracket_tones else ""

    token_wo_bracket = _BRACKET_TONE_RE.sub("", raw)
    neutral = token_wo_bracket.endswith("0") and len(token_wo_bracket) > 1
    if neutral:
        token_wo_bracket = token_wo_bracket[:-1]

    m = _TRAILING_DIGITS_RE.search(token_wo_bracket)
    if m:
        base_tone = m.group(1)
        body = token_wo_bracket[: m.start()]
    else:
        base_tone = ""
        body = token_wo_bracket

    return ParsedToken(
        raw=raw,
        body=body,
        base_tone=base_tone,
        sandhi_tone=sandhi_tone,
        neutral=neutral,
    )


def _normalize_tone_digits(tone_digits: str) -> str:
    """
    将类别声调 1-8 映射到 5 度调值数字；其余认为已是调值数字，直接返回。
    """
    if not tone_digits:
        return ""
    if len(tone_digits) == 1 and tone_digits in TONE_CATEGORY_TO_CHAO:
        return TONE_CATEGORY_TO_CHAO[tone_digits]
    return tone_digits


def split_onset_rime(body: str) -> Tuple[str, str]:
    """
    按最长匹配切分声母/韵母；无声母则返回 ("", body)。
    """
    for onset in _ONSETS_LONGEST_FIRST:
        if body.startswith(onset):
            return onset, body[len(onset) :]
    return "", body


def rime_to_ipa(rime: str) -> Optional[str]:
    """
    韵母转写（不含声母与声调）。返回 None 表示无法识别。
    """
    if rime == "":
        return ""

    if rime in CHECKED_RIME_TO_IPA:
        return CHECKED_RIME_TO_IPA[rime]

    if rime in RIME_ATOMIC_TO_IPA:
        return RIME_ATOMIC_TO_IPA[rime]

    # 介音递归（i-/u-）
    if rime.startswith("i"):
        sub = rime_to_ipa(rime[1:])
        return None if sub is None else "i" + sub
    if rime.startswith("u"):
        sub = rime_to_ipa(rime[1:])
        return None if sub is None else "u" + sub

    return None


def wupin_body_to_ipa(body: str) -> Optional[str]:
    """
    不含声调的音节体（仅小写字母+q/h）→ IPA（不含声调数字）。
    """
    if not body:
        return ""

    # 避免处理明显损坏/粘连（如 eu223dou）
    if any(ch.isdigit() for ch in body):
        return None

    # y- 系列零声母：约定为 ɦ + i/iu 系列
    if body == "y":
        ipa_rime = rime_to_ipa("y")
        return ipa_rime
    if body.startswith("y") and len(body) > 1:
        rest = body[1:]
        # 模拟普通拼音的 y- 规则：yu* 视作 iu*，其余视作 i*
        if rest.startswith("u"):
            pseudo_rime = "i" + rest
        elif rest.startswith("i"):
            pseudo_rime = rest
        else:
            pseudo_rime = "i" + rest
        ipa_rime = rime_to_ipa(pseudo_rime)
        return None if ipa_rime is None else "ɦ" + ipa_rime

    onset, rime = split_onset_rime(body)
    ipa_onset = ONSET_TO_IPA.get(onset, onset)
    ipa_rime = rime_to_ipa(rime)
    if ipa_rime is None:
        return None
    return ipa_onset + ipa_rime


def wupin_token_to_ipa(token: str, tone: str = "sandhi") -> str:
    """
    单 token 转写为 IPA。

    Args:
        token: wupin token（可含 [..]、声调数字、轻声 0）
        tone: none/base/sandhi
    """
    parsed = parse_wupin_token(token)
    body = parsed.body.strip()
    ipa_body = wupin_body_to_ipa(body)
    if ipa_body is None or ipa_body == "":
        return "?"

    if tone == "none":
        return ipa_body

    if tone == "base":
        tone_digits = parsed.base_tone
    else:  # sandhi (default)
        tone_digits = parsed.sandhi_tone or parsed.base_tone

    tone_digits = _normalize_tone_digits(tone_digits)
    return ipa_body + tone_digits


def wupin_key_to_ipa(key: str, tone: str = "sandhi") -> str:
    """
    整行 key（可含空格/逗号）逐 token 转写并保留分隔符。
    """
    parts = re.split(r"(\s+|,)", key)
    # 修正少量“声调数字被空格拆开”的 key，如 "soq 7" / "zaon 231"
    merged = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if not part:
            i += 1
            continue

        if part.isspace() and i + 1 < len(parts) and parts[i + 1] and parts[i + 1][0].isdigit():
            # 丢弃这段空白，让下一个纯数字 token 附着到前一个音节上
            i += 1
            continue

        if part[0].isdigit() and merged and merged[-1] not in {","} and not merged[-1].isspace():
            merged[-1] = f"{merged[-1]}{part}"
            i += 1
            continue

        merged.append(part)
        i += 1

    out = []
    for part in merged:
        if not part:
            continue
        if part.isspace() or part == ",":
            out.append(part)
            continue
        out.append(wupin_token_to_ipa(part, tone=tone))
    return "".join(out).strip()

#!/usr/bin/env python3
"""
吴语拼音转换器 - Greedy 分词 + Fallback
"""

from dataclasses import dataclass
from typing import List, Optional, Generator
from .loader import DataLoader


@dataclass
class Segment:
    """
    分词片段结果
    
    Attributes:
        text: 原始文本
        pinyin: 拼音
        is_word: True 表示来自 words.json，False 表示来自 char_base.json
        alternatives: 多音字的备选读音（仅单字有）
    """
    text: str
    pinyin: str
    is_word: bool
    alternatives: List[str] = None
    
    def __repr__(self) -> str:
        return f"Segment({self.text!r}: {self.pinyin!r})"


class WuConverter:
    """
    吴语拼音转换器
    
    算法：
    1. 从文本开头开始，使用 greedy 策略在 words.json 中匹配最长词语
    2. 如果匹配成功，记录词语拼音，跳过该词语长度
    3. 如果匹配失败（未找到词语），fall back 到 char_base.json 查单字
    4. 重复直到文本结束
    """
    
    # 最大词语长度限制（防止过长匹配降低性能）
    MAX_WORD_LEN = 15
    
    def __init__(self, loader: DataLoader):
        """
        初始化转换器
        
        Args:
            loader: 已加载的数据加载器
        """
        self.loader = loader
        if not loader._loaded:
            loader.load()
    
    def convert(self, text: str, max_word_len: int = None) -> List[Segment]:
        """
        将中文文本转换为吴语拼音
        
        Args:
            text: 输入文本（简体汉字）
            max_word_len: 最大匹配词语长度，默认使用 self.MAX_WORD_LEN
            
        Returns:
            Segment 列表
        """
        if max_word_len is None:
            max_word_len = self.MAX_WORD_LEN
        
        result = []
        i = 0
        text_len = len(text)
        
        while i < text_len:
            char = text[i]
            
            # 跳过非汉字字符（标点、空格、数字等）
            if not self._is_chinese(char):
                result.append(Segment(
                    text=char,
                    pinyin=char,  # 保持原样
                    is_word=False,
                    alternatives=[]
                ))
                i += 1
                continue
            
            # Greedy 匹配：从最长可能开始
            matched = False
            remaining_len = min(max_word_len, text_len - i)
            
            for length in range(remaining_len, 1, -1):
                substr = text[i:i+length]
                
                # 检查是否全是汉字
                if not all(self._is_chinese(c) for c in substr):
                    continue
                
                pinyin = self.loader.get_word_pinyin(substr)
                if pinyin:
                    result.append(Segment(
                        text=substr,
                        pinyin=pinyin,
                        is_word=True,
                        alternatives=[]
                    ))
                    i += length
                    matched = True
                    break
            
            if not matched:
                # Fallback 到单字
                pinyin = self.loader.get_char_pinyin(char)
                alternatives = self.loader.get_char_alternatives(char)
                
                result.append(Segment(
                    text=char,
                    pinyin=pinyin or "?",  # 未找到用 ? 标记
                    is_word=False,
                    alternatives=alternatives if len(alternatives) > 1 else []
                ))
                i += 1
        
        return result
    
    def convert_to_string(self, text: str, separator: str = " ", max_word_len: int = None) -> str:
        """
        转换为拼音字符串
        
        Args:
            text: 输入文本
            separator: 分隔符，默认空格
            max_word_len: 最大匹配词语长度
            
        Returns:
            拼音字符串
        """
        segments = self.convert(text, max_word_len)
        return separator.join(s.pinyin for s in segments)
    
    def convert_with_detail(self, text: str, max_word_len: int = None) -> dict:
        """
        带详细信息的转换
        
        Returns:
            {
                "text": 原始文本,
                "pinyin": 完整拼音,
                "segments": [Segment, ...]
            }
        """
        segments = self.convert(text, max_word_len)
        return {
            "text": text,
            "pinyin": " ".join(s.pinyin for s in segments),
            "segments": segments
        }
    
    def convert_iter(self, text: str, max_word_len: int = None) -> Generator[Segment, None, None]:
        """
        生成器版本的转换（用于大文本流式处理）
        
        Yields:
            Segment 对象
        """
        if max_word_len is None:
            max_word_len = self.MAX_WORD_LEN
        
        i = 0
        text_len = len(text)
        
        while i < text_len:
            char = text[i]
            
            if not self._is_chinese(char):
                yield Segment(text=char, pinyin=char, is_word=False)
                i += 1
                continue
            
            matched = False
            remaining_len = min(max_word_len, text_len - i)
            
            for length in range(remaining_len, 1, -1):
                substr = text[i:i+length]
                if not all(self._is_chinese(c) for c in substr):
                    continue
                
                pinyin = self.loader.get_word_pinyin(substr)
                if pinyin:
                    yield Segment(text=substr, pinyin=pinyin, is_word=True)
                    i += length
                    matched = True
                    break
            
            if not matched:
                pinyin = self.loader.get_char_pinyin(char) or "?"
                yield Segment(text=char, pinyin=pinyin, is_word=False)
                i += 1
    
    @staticmethod
    def _is_chinese(char: str) -> bool:
        """检查字符是否是汉字（CJK统一汉字）"""
        return '\u4e00' <= char <= '\u9fff'
    
    def get_stats(self) -> dict:
        """获取数据加载统计信息"""
        return {
            "word_count": self.loader.word_count,
            "char_count": self.loader.char_count,
        }

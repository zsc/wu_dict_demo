#!/usr/bin/env python3
"""
加载 words.json 和 char_base.json 数据文件
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional


def get_default_data_dir() -> Path:
    """获取默认数据目录"""
    # 1. 首先尝试从模块所在目录查找（开发模式）
    module_dir = Path(__file__).parent
    dev_data_dir = module_dir / ".." / ".." / "data"
    if dev_data_dir.exists():
        return dev_data_dir.resolve()
    
    # 2. 尝试从包内查找（安装后）
    pkg_data_dir = module_dir / "data"
    if pkg_data_dir.exists():
        return pkg_data_dir
    
    # 3. 从环境变量查找
    env_data_dir = os.environ.get("WU_PINYIN_DATA")
    if env_data_dir:
        return Path(env_data_dir)
    
    # 默认返回当前目录下的 data
    return Path("data")


class DataLoader:
    """
    加载和管理吴语拼音数据文件
    
    - words.json: {词语: 拼音}，用于 greedy 匹配
    - char_base.json: {单字: [拼音列表]}，用于 fallback
    """
    
    def __init__(self, data_dir: str = None):
        """
        初始化数据加载器
        
        Args:
            data_dir: 数据文件目录，默认自动检测
        """
        if data_dir is None:
            self.data_dir = get_default_data_dir()
        else:
            self.data_dir = Path(data_dir)
        
        self.words: Dict[str, str] = {}
        self.char_base: Dict[str, List[str]] = {}
        self._loaded = False
    
    def load(self) -> None:
        """加载数据文件"""
        if self._loaded:
            return
        
        words_path = self.data_dir / "words.json"
        char_path = self.data_dir / "char_base.json"
        
        if not words_path.exists():
            raise FileNotFoundError(
                f"words.json not found: {words_path}\n"
                "Please run: python -m wu_pinyin.builder"
            )
        if not char_path.exists():
            raise FileNotFoundError(
                f"char_base.json not found: {char_path}\n"
                "Please run: python -m wu_pinyin.builder"
            )
        
        with open(words_path, 'r', encoding='utf-8') as f:
            self.words = json.load(f)
        
        with open(char_path, 'r', encoding='utf-8') as f:
            self.char_base = json.load(f)
        
        self._loaded = True
        
    def get_word_pinyin(self, word: str) -> Optional[str]:
        """
        查询词语拼音
        
        Args:
            word: 简体词语
            
        Returns:
            拼音字符串，未找到返回 None
        """
        return self.words.get(word)
    
    def get_char_pinyin(self, char: str) -> Optional[str]:
        """
        查询单字拼音（返回最常见读音，即第一个）
        
        Args:
            char: 单字符
            
        Returns:
            拼音字符串，未找到返回 None
        """
        pinyins = self.char_base.get(char)
        return pinyins[0] if pinyins else None
    
    def get_char_alternatives(self, char: str) -> List[str]:
        """
        查询单字所有读音
        
        Args:
            char: 单字符
            
        Returns:
            拼音列表，未找到返回空列表
        """
        return self.char_base.get(char, [])
    
    def word_exists(self, word: str) -> bool:
        """检查词语是否存在"""
        return word in self.words
    
    def char_exists(self, char: str) -> bool:
        """检查单字是否存在"""
        return char in self.char_base
    
    @property
    def word_count(self) -> int:
        """词语数量"""
        return len(self.words)
    
    @property
    def char_count(self) -> int:
        """单字数量"""
        return len(self.char_base)

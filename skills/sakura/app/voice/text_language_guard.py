from __future__ import annotations

import re


_JAPANESE_KANA_RE = re.compile(r"[\u3040-\u30ff\uff66-\uff9f]")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

_CHINESE_MARKERS = (
    "这个",
    "那个",
    "这些",
    "那些",
    "如果",
    "因为",
    "所以",
    "但是",
    "然后",
    "应该",
    "可以",
    "需要",
    "不能",
    "不会",
    "没有",
    "已经",
    "还是",
    "一下",
    "看看",
    "打开",
    "确认",
    "问题",
    "原因",
    "错误",
    "语法",
    "字符串",
    "节点",
)
_CHINESE_PUNCTUATION = "，？！；："
_COMMON_CHINESE_CHARS = set("我你的是了在有和不这那们把里吗吧呢")
_SIMPLIFIED_ONLY_CHARS = set("语错该节显这们为会览进开关")


def should_skip_tts_text(text: str, target_lang: str) -> bool:
    """目标语音为日语时，明显中文的文本不送入 TTS。"""
    if not text.strip():
        return False

    normalized_lang = target_lang.strip().lower()
    if normalized_lang not in {"ja", "all_ja"}:
        return False

    return _looks_obvious_chinese(text)


def _looks_obvious_chinese(text: str) -> bool:
    if _JAPANESE_KANA_RE.search(text):
        return False
    if not _CJK_RE.search(text):
        return False
    return (
        any(marker in text for marker in _CHINESE_MARKERS)
        or any(char in _CHINESE_PUNCTUATION for char in text)
        or sum(1 for char in text if char in _COMMON_CHINESE_CHARS) >= 2
        or any(char in _SIMPLIFIED_ONLY_CHARS for char in text)
    )

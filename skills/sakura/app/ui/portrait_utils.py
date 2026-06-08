from __future__ import annotations

import re
from pathlib import Path


def portrait_kind_key(path: Path) -> str:
    """从 A020/B180/I010 这类新立绘编号中提取姿态种类。"""
    match = re.fullmatch(r"([A-Za-z])\d+", path.stem)
    if match is None:
        return ""
    return match.group(1).upper()


def should_crossfade_portrait(previous_path: Path, next_path: Path) -> bool:
    """只要切换到不同立绘，就执行淡入淡出过渡。"""
    return previous_path != next_path

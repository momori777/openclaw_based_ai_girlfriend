from __future__ import annotations

import os
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class NotesStore:
    """限制在 data/notes 下的文本笔记工具。"""

    def __init__(self, notes_dir: Path) -> None:
        self.notes_dir = notes_dir

    def read_note(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_note_path(_required_text(arguments, "name"))
        if not path.exists():
            raise ValueError(f"笔记不存在：{path.name}")
        if not path.is_file():
            raise ValueError(f"不是笔记文件：{path.name}")
        return {
            "name": path.name,
            "content": path.read_text(encoding="utf-8"),
        }

    def write_note(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_note_path(_required_text(arguments, "name"))
        content = _required_text(arguments, "content")
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(content + "\n", encoding="utf-8")
        return {
            "name": path.name,
            "bytes": path.stat().st_size,
        }

    def _resolve_note_path(self, name: str) -> Path:
        if any(separator in name for separator in ("/", "\\")):
            raise ValueError("笔记名不能包含路径分隔符。")
        if name in {".", ".."}:
            raise ValueError("笔记名无效。")
        if not name.endswith(".txt"):
            name = f"{name}.txt"

        base = self.notes_dir.resolve()
        path = (self.notes_dir / name).resolve()
        if path.parent != base:
            raise ValueError("笔记路径必须位于 data/notes 内。")
        return path


def open_url(arguments: dict[str, Any]) -> dict[str, Any]:
    url = _required_text(arguments, "url")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL 只支持 http:// 或 https://。")
    opened = webbrowser.open(url)
    return {
        "url": url,
        "opened": opened,
    }


def open_local_folder(arguments: dict[str, Any]) -> dict[str, Any]:
    path_text = _required_text(arguments, "path")
    path = Path(path_text).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"文件夹不存在：{path}")
    if not path.is_dir():
        raise ValueError(f"不是文件夹：{path}")

    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        webbrowser.open(path.as_uri())
    return {
        "path": str(path),
        "opened": True,
    }


def _required_text(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"缺少必填参数：{key}")
    return value.strip()

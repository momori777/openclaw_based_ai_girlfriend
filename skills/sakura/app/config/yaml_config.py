from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """读取 YAML mapping；缺失、空文件或非 mapping 时返回空字典。"""
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML 配置格式无效：{path}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML 配置必须是对象：{path}")
    return dict(data)


def save_yaml_mapping(path: Path, data: dict[str, Any]) -> None:
    """保存 YAML mapping，保留中文并使用稳定顺序。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            data,
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

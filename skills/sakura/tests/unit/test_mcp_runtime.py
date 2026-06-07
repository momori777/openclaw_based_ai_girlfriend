from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

import app.agent.mcp.provider as mcp_provider_module
from app.agent.mcp.bridge import MCPBridge
from app.agent.mcp.config import MCPServerConfig, load_mcp_config


def test_mcp_runtime_token_prefers_current_python_scripts(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _runtime_root_path("mcp_uv_runtime_token")
    python_dir = root / "runtime"
    scripts_dir = python_dir / "Scripts"
    scripts_dir.mkdir(parents=True)
    python_exe = python_dir / ("python.exe" if sys.platform == "win32" else "python")
    python_exe.write_text("", encoding="utf-8")
    uv_exe = scripts_dir / ("uv.exe" if sys.platform == "win32" else "uv")
    uv_exe.write_text("", encoding="utf-8")
    config_path = root / "mcp.yaml"
    config_path.write_text(
        """
enabled: true
servers:
  windows:
    enabled: true
    transport: stdio
    command: "{uv}"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(mcp_provider_module.sys, "executable", str(python_exe))

    resolved = mcp_provider_module._resolve_runtime_tokens(load_mcp_config(config_path), root)

    assert resolved.servers[0].command == str(uv_exe)


def test_mcp_bridge_missing_stdio_command_has_actionable_error() -> None:
    bridge = MCPBridge(
        MCPServerConfig(
            name="windows",
            transport="stdio",
            command=f"sakura_missing_mcp_command_{uuid.uuid4().hex}",
        ),
        default_call_timeout=1,
    )

    with pytest.raises(RuntimeError) as exc_info:
        bridge.connect()

    error = str(exc_info.value)
    assert "找不到命令" in error
    assert "install.bat" in error
    assert "WinError" not in error
    bridge.close()


def _runtime_root_path(name: str) -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "__pycache__"
        / "test_runtime"
        / name
        / uuid.uuid4().hex
    )

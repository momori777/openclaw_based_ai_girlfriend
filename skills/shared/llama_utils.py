"""
共享工具模块 — llama-server 生命周期感知

被 tts_call.py、comfyui_call.py 和 Sakura local_llama_client.py 共用。
消除三份代码中重复的 _port_open / _wait_for_llama_ready 实现。

原则：
- 只做检测，不做 kill/restart
- TTS/ComfyUI 继续负责 kill + restart
- Sakura 只用 detect_and_wait 感知恢复
"""

from __future__ import annotations

import json
import socket
import time
import urllib.request
from typing import Callable

# ── 端口探测 ──────────────────────────────────────────────────

def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """检测 TCP 端口是否可达。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ── 不可用检测 ────────────────────────────────────────────────

def detect_llama_unavailable(error: BaseException) -> bool:
    """判断 HTTP 错误是否由本地 llama 不可用（被 TTS/ComfyUI 杀死）引起。"""
    text = str(error).lower()
    markers = (
        "connection refused",
        "connection reset",
        "refused",
        "timeout",
        "timed out",
        "500",
        "502",
        "503",
        "504",
        "no connection",
        "could not connect",
        "unreachable",
        "connection aborted",
        "broken pipe",
        "remote end closed",
    )
    return any(m in text for m in markers)


# ── 健康检查 ──────────────────────────────────────────────────

def _health_ok(port: int, timeout: float = 5.0) -> bool:
    """HTTP /health 返回 200。"""
    try:
        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/health", timeout=timeout
        )
        return resp.status == 200
    except Exception:
        return False


def _completion_ok(port: int, timeout: float = 10.0) -> bool:
    """发最小 completion 请求验证模型可推理。"""
    test_payload = json.dumps({
        "prompt": "hi",
        "n_predict": 1,
        "temperature": 0,
        "cache_prompt": False,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/completion",
            data=test_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "***",
            },
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        if resp.status == 200:
            data = json.loads(resp.read())
            return bool(data.get("content") is not None or data.get("stop"))
    except Exception:
        pass
    return False


# ── 三阶段就绪检测（主入口）────────────────────────────────────

def wait_for_llama_ready(
    port: int = 8080,
    timeout: float = 300.0,
    *,
    log: Callable[[str], None] | None = None,
    poll_interval: float = 2.0,
) -> bool:
    """三阶段验证 llama-server 完全就绪。

    阶段1: TCP 端口打开
    阶段2: HTTP /health 200（模型已加载）
    阶段3: /completion 实际推理响应

    返回 True 表示模型可接受推理请求。
    与 TTS/ComfyUI 的 start_llama() 后等待逻辑一致。
    """
    def _log(msg: str) -> None:
        if log:
            log(msg)

    deadline = time.monotonic() + timeout

    # 阶段1: 端口
    _log(f"[LLAMA] 等待端口 {port}...")
    while time.monotonic() < deadline:
        if port_open("127.0.0.1", port, timeout=2):
            _log(f"[LLAMA] 端口 {port} 已打开")
            break
        time.sleep(poll_interval)
    else:
        _log(f"[LLAMA] 端口 {port} 在 {timeout}s 内未打开")
        return False

    # 阶段2: /health
    _log("[LLAMA] 等待 /health 200（模型加载中）...")
    while time.monotonic() < deadline:
        if _health_ok(port):
            _log("[LLAMA] /health 200 — 模型已加载")
            break
        time.sleep(poll_interval)

    # 阶段3: /completion
    _log("[LLAMA] 验证 /completion 可推理...")
    while time.monotonic() < deadline:
        if _completion_ok(port):
            _log("[LLAMA] /completion 通过 — 就绪 ✓")
            return True
        time.sleep(poll_interval)

    _log(f"[LLAMA] /completion 在超时前未响应，但端口可用，允许尝试")
    return _health_ok(port)  # 至少 health 过了


# ── 便捷函数：一次性检测 ─────────────────────────────────────

def is_llama_ready(port: int = 8080) -> bool:
    """快速检测 llama-server 是否可接受请求（不阻塞）。"""
    if not port_open("127.0.0.1", port, timeout=2):
        return False
    return _completion_ok(port, timeout=5)

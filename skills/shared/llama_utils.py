"""
Shared utility module — llama-server lifecycle awareness.

Used by tts_call.py, comfyui_call.py, and Sakura's local_llama_client.py.
Eliminates duplicated port_open / wait_for_llama_ready across three codebases.

Principle:
- Detection only, no kill/restart
- TTS/ComfyUI handle kill + restart via llama_lifecycle.py
- Sakura uses detect_llama_unavailable + wait_for_llama_ready for recovery sensing
"""

from __future__ import annotations

import json
import socket
import time
import urllib.request
from typing import Callable


# ---- Port probe ----

def port_open(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    """Check if TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


# ---- Unavailability detection ----

def detect_llama_unavailable(exc: object = None) -> bool:
    """Return True if local llama is unavailable (killed by TTS/ComfyUI).

    If an exception object is provided, check its characteristics first.
    Otherwise fall back to port + /health actual check.
    """
    if exc is not None:
        return _exc_indicates_llama_dead(exc)
    return not _health_ok(8080)


def _exc_indicates_llama_dead(exc: object) -> bool:
    """Heuristic: does this exception look like llama was killed?"""
    try:
        status = getattr(exc, 'status_code', None) or getattr(exc, 'status', None)
        if status == 500:
            return True
        body = str(exc).lower()
        for hint in (
            'connection refused', 'no connection', 'timeout',
            'reset by peer', 'broken pipe', 'connectionreset',
            'max retries',
        ):
            if hint in body:
                return True
    except Exception:
        pass
    return not port_open(8080)


# ---- Health checks ----

def _health_ok(port: int, timeout: float = 5.0) -> bool:
    """HTTP /health returns 200."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _completion_ok(port: int, timeout: float = 10.0) -> bool:
    """Send a minimal completion probe to verify model can infer."""
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                body = resp.read()
                data = json.loads(body)
                return bool(data.get("content") or data.get("stop"))
    except Exception:
        pass
    return False


def _chat_completions_ok(port: int, timeout: float = 10.0) -> bool:
    """Verify /v1/chat/completions endpoint (what OpenClaw actually uses)."""
    test_payload = json.dumps({
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "temperature": 0,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=test_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer 123456",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                body = resp.read()
                data = json.loads(body)
                return bool(data.get("choices"))
    except Exception:
        pass
    return False


# ---- Four-phase readiness check (main entry) ----

def wait_for_llama_ready(
    port: int = 8080,
    timeout: float = 300.0,
    *,
    log: Callable[[str], None] | None = None,
    poll_interval: float = 2.0,
) -> bool:
    """Four-phase validation for llama-server fully ready.

    Phase 1: TCP port open
    Phase 2: HTTP /health 200 (model loaded)
    Phase 3: /completion actual inference response
    Phase 4: /v1/chat/completions (what OpenClaw uses)

    Returns True when model can accept OpenClaw inference requests.
    Consistent with start_llama() wait logic in TTS/ComfyUI scripts.
    """
    def _log(msg: str) -> None:
        if log:
            log(msg)

    deadline = time.monotonic() + timeout

    # Phase 1: port
    _log(f"[LLAMA] Waiting for port {port}...")
    while time.monotonic() < deadline:
        if port_open(port):
            _log(f"[LLAMA] Port {port} open")
            break
        time.sleep(poll_interval)
    else:
        _log(f"[LLAMA] Port {port} not open within {timeout}s")
        return False

    # Phase 2: /health
    _log("[LLAMA] Waiting for /health 200 (model loading)...")
    while time.monotonic() < deadline:
        if _health_ok(port):
            _log("[LLAMA] /health 200 — model loaded")
            break
        time.sleep(poll_interval)

    # Phase 3: /completion
    _log("[LLAMA] Verifying /completion probe...")
    while time.monotonic() < deadline:
        if _completion_ok(port):
            _log("[LLAMA] /completion passed")
            break
        time.sleep(poll_interval)

    # Phase 4: /v1/chat/completions (what OpenClaw actually uses)
    _log("[LLAMA] Verifying /v1/chat/completions probe...")
    while time.monotonic() < deadline:
        if _chat_completions_ok(port):
            _log("[LLAMA] /v1/chat/completions passed — ready")
            return True
        time.sleep(poll_interval)

    _log("[LLAMA] /v1/chat/completions not responding before timeout, port open — allow attempt")
    return _health_ok(port)  # at least health passed


# ---- Quick check ----

def is_llama_ready(port: int = 8080) -> bool:
    """Quick check if llama-server can accept requests (non-blocking)."""
    if not port_open(port, timeout=2):
        return False
    return _completion_ok(port, timeout=5)

"""Llama server lifecycle utilities.

Used by Sakura's LocalLlamaClient for recovery sensing.
Shared with TTS/ComfyUI scripts via skills/shared/llama_utils.py
(which is the authoritative copy — keep signatures in sync).
"""

import json
import socket
import time
import urllib.error
import urllib.request

_LLAMA_HEALTH_URL = "http://localhost:8080/health"
_LLAMA_PORT = 8080


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    """Check if a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def detect_llama_unavailable(exc: object = None) -> bool:
    """Return True if llama health endpoint is unreachable or non-200.

    If *exc* is provided (ApiRequestError), first check whether it looks
    like the local llama was killed (HTTP 500 with 'llama' in body).
    """
    if exc is not None:
        return _exc_indicates_llama_dead(exc)
    try:
        req = urllib.request.Request(_LLAMA_HEALTH_URL)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            return resp.status != 200
    except Exception:
        return True


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
    return not port_open(_LLAMA_PORT)


def wait_for_llama_ready(
    port: int = 8080,
    timeout: float = 300.0,
) -> bool:
    """Block until llama-server /health returns 200 and a completion probe works,
    or timeout expires. Returns True if ready, False on timeout.
    """
    deadline = time.monotonic() + timeout

    # Phase 1: wait for port open
    while time.monotonic() < deadline:
        if port_open(port):
            break
        time.sleep(2.0)
    else:
        return False

    # Phase 2: wait for /health 200
    while time.monotonic() < deadline:
        if not detect_llama_unavailable():
            # Phase 3: quick completion probe
            if _probe_completion(port):
                return True
        time.sleep(3.0)

    return False


def _probe_completion(port: int) -> bool:
    """Send a tiny completion request to confirm llama is fully loaded."""
    data = json.dumps({
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"http://localhost:{port}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return resp.status == 200
    except Exception:
        return False

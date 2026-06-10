"""Inline llama utils — extracted from damaged llama_utils.py to fix UTF-16 encoding issue."""

import time
import urllib.request
import urllib.error

_LLAMA_HEALTH_URL = "http://localhost:8080/health"
_LLAMA_PORT = 8080


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    """Check if a TCP port is accepting connections."""
    import socket
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
    # Quick filter: if the error doesn't smell like llama-down, return False
    if exc is not None:
        return _exc_indicates_llama_dead(exc)
    # Standalone health check
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
        for hint in ('connection refused', 'no connection', 'timeout',
                      'reset by peer', 'broken pipe', 'connectionreset',
                      'max retries'):
            if hint in body:
                return True
    except Exception:
        pass
    return not port_open(_LLAMA_PORT)


def wait_for_llama_ready(timeout_seconds: int = 300) -> bool:
    """Block until llama-server /health returns 200 and a completion probe works,
    or timeout expires. Returns True if ready, False on timeout.
    """
    deadline = time.time() + timeout_seconds
    # Phase 1: wait for port open
    while time.time() < deadline:
        if port_open(_LLAMA_PORT):
            break
        time.sleep(2.0)
    else:
        return False

    # Phase 2: wait for /health 200
    while time.time() < deadline:
        if not detect_llama_unavailable():
            # Phase 3: quick completion probe
            if _probe_completion():
                return True
        time.sleep(3.0)

    return False


def _probe_completion() -> bool:
    """Send a tiny completion request to confirm llama is fully loaded."""
    import json
    data = json.dumps({
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8080/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return resp.status == 200
    except Exception:
        return False

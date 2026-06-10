"""
鍏变韩宸ュ叿妯″潡 鈥?llama-server 鐢熷懡鍛ㄦ湡鎰熺煡

琚?tts_call.py銆乧omfyui_call.py 鍜?Sakura local_llama_client.py 鍏辩敤銆?娑堥櫎涓変唤浠ｇ爜涓噸澶嶇殑 _port_open / _wait_for_llama_ready 瀹炵幇銆?
鍘熷垯锛?- 鍙仛妫€娴嬶紝涓嶅仛 kill/restart
- TTS/ComfyUI 缁х画璐熻矗 kill + restart
- Sakura 鍙敤 detect_and_wait 鎰熺煡鎭㈠
"""

from __future__ import annotations

import json
import socket
import time
import urllib.request
from typing import Callable

# 鈹€鈹€ 绔彛鎺㈡祴 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """妫€娴?TCP 绔彛鏄惁鍙揪銆?""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# 鈹€鈹€ 涓嶅彲鐢ㄦ娴?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def detect_llama_unavailable(error: BaseException) -> bool:
    """鍒ゆ柇 HTTP 閿欒鏄惁鐢辨湰鍦?llama 涓嶅彲鐢紙琚?TTS/ComfyUI 鏉€姝伙級寮曡捣銆?""
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


# 鈹€鈹€ 鍋ュ悍妫€鏌?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def _health_ok(port: int, timeout: float = 5.0) -> bool:
    """HTTP /health 杩斿洖 200銆?""
    try:
        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/health", timeout=timeout
        )
        return resp.status == 200
    except Exception:
        return False


def _completion_ok(port: int, timeout: float = 10.0) -> bool:
    """鍙戞渶灏?completion 璇锋眰楠岃瘉妯″瀷鍙帹鐞嗐€?""
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


# 鈹€鈹€ 涓夐樁娈靛氨缁娴嬶紙涓诲叆鍙ｏ級鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def wait_for_llama_ready(
    port: int = 8080,
    timeout: float = 300.0,
    *,
    log: Callable[[str], None] | None = None,
    poll_interval: float = 2.0,
) -> bool:
    """涓夐樁娈甸獙璇?llama-server 瀹屽叏灏辩华銆?
    闃舵1: TCP 绔彛鎵撳紑
    闃舵2: HTTP /health 200锛堟ā鍨嬪凡鍔犺浇锛?    闃舵3: /completion 瀹為檯鎺ㄧ悊鍝嶅簲

    杩斿洖 True 琛ㄧず妯″瀷鍙帴鍙楁帹鐞嗚姹傘€?    涓?TTS/ComfyUI 鐨?start_llama() 鍚庣瓑寰呴€昏緫涓€鑷淬€?    """
    def _log(msg: str) -> None:
        if log:
            log(msg)

    deadline = time.monotonic() + timeout

    # 闃舵1: 绔彛
    _log(f"[LLAMA] 绛夊緟绔彛 {port}...")
    while time.monotonic() < deadline:
        if port_open("127.0.0.1", port, timeout=2):
            _log(f"[LLAMA] 绔彛 {port} 宸叉墦寮€")
            break
        time.sleep(poll_interval)
    else:
        _log(f"[LLAMA] 绔彛 {port} 鍦?{timeout}s 鍐呮湭鎵撳紑")
        return False

    # 闃舵2: /health
    _log("[LLAMA] 绛夊緟 /health 200锛堟ā鍨嬪姞杞戒腑锛?..")
    while time.monotonic() < deadline:
        if _health_ok(port):
            _log("[LLAMA] /health 200 鈥?妯″瀷宸插姞杞?)
            break
        time.sleep(poll_interval)

    # 闃舵3: /completion
    _log("[LLAMA] 楠岃瘉 /completion 鍙帹鐞?..")
    while time.monotonic() < deadline:
        if _completion_ok(port):
            _log("[LLAMA] /completion 閫氳繃 鈥?灏辩华 鉁?)
            return True
        time.sleep(poll_interval)

    _log(f"[LLAMA] /completion 鍦ㄨ秴鏃跺墠鏈搷搴旓紝浣嗙鍙ｅ彲鐢紝鍏佽灏濊瘯")
    return _health_ok(port)  # 鑷冲皯 health 杩囦簡


# 鈹€鈹€ 渚挎嵎鍑芥暟锛氫竴娆℃€ф娴?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

def is_llama_ready(port: int = 8080) -> bool:
    """蹇€熸娴?llama-server 鏄惁鍙帴鍙楄姹傦紙涓嶉樆濉烇級銆?""
    if not port_open("127.0.0.1", port, timeout=2):
        return False
    return _completion_ok(port, timeout=5)

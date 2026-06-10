"""
共享 Llama Server 生命周期管理模块。

提供统一的 llama-server 启停、文件锁、硬超时守卫和清理钩子，
供 tts_call.py 和 comfyui_call.py 复用，消除 ~270 行重复代码。

用法：
    import sys, os
    _dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _dir not in sys.path:
        sys.path.insert(0, _dir)
    from skills.shared.llama_lifecycle import (
        acquire_lock, release_lock,
        stop_llama, start_llama,
        TimeoutGuard, register_cleanup_handlers,
    )

    # 获取锁
    pid, exe = acquire_lock(
        lock_file=os.path.join(OUTPUT_DIR, ".my_skill_running.lock"),
        label="my_skill"
    )
    if pid is None:
        return  # 已有实例在运行

    # 注册清理钩子
    register_cleanup_handlers(
        lock_file=os.path.join(OUTPUT_DIR, ".my_skill_running.lock"),
        llama_port=LLAMA_PORT,
        restart_script=RESTART_SCRIPT,
    )

    with TimeoutGuard(300):
        stop_llama(port=LLAMA_PORT, wait_vram_stable=True)
        do_my_work()
        start_llama(
            port=LLAMA_PORT,
            exe_path=LLAMA_EXE_PATH,
            model_path=LLAMA_MODEL_PATH,
            log_dir=LLAMA_LOG_DIR,
        )
"""

import os
import sys
import time
import json
import atexit
import signal
import subprocess
import threading


# ---- 共享底层（端口检测 / 健康检查） ----

def _port_open(host, port, timeout=2):
    """检测指定端口是否开启"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False
    finally:
        s.close()


def _wait_for_vram_stable(initial_free=None, stable_threshold=50, max_wait=30,
                          min_free_mb=None, label="[LLAMA]"):
    """
    等待 CUDA VRAM 稳定（释放完成）。

    参数：
        initial_free: 初始空闲 VRAM (MiB)；如果为 None 则自动获取
        stable_threshold: 两次检测差值 < 此值即认为稳定 (MiB)
        max_wait: 最大等待时间 (秒)
        min_free_mb: 要求至少空闲这么多 MiB 才返回（如 6000=llama 需要 ~5.8GB）

    返回最终稳定时的空闲 VRAM (MiB)。如果 max_wait 内达不到 min_free_mb 则最多等到底。
    """
    try:
        import torch
        if not torch.cuda.is_available():
            print(f"{label} torch CUDA not available", file=sys.stderr, flush=True)
            time.sleep(3)  # fallback wait
            return 0

        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        if initial_free is None:
            initial_free = torch.cuda.mem_get_info()[0] / (1024 ** 2)
        free_vram = initial_free
        print(f"{label} CUDA sync done, free VRAM: {free_vram:.0f} MiB",
              file=sys.stderr, flush=True)

        stable_count = 0
        peak_free = free_vram
        for i in range(max_wait):
            time.sleep(1)
            cur_free = torch.cuda.mem_get_info()[0] / (1024 ** 2)
            peak_free = max(peak_free, cur_free)
            if abs(cur_free - free_vram) < stable_threshold:
                stable_count += 1
                if stable_count >= 3:  # 连续 3s 内波动 < threshold
                    if min_free_mb and cur_free < min_free_mb:
                        print(f"{label} VRAM stable at {cur_free:.0f} MiB but below "
                              f"{min_free_mb} MiB minimum, waiting more...",
                              file=sys.stderr, flush=True)
                        stable_count = 0  # reset, keep waiting
                        free_vram = cur_free
                        continue
                    print(f"{label} VRAM stable at {cur_free:.0f} MiB "
                          f"(peak {peak_free:.0f}, {i + 1}s)",
                          file=sys.stderr, flush=True)
                    return cur_free
            else:
                stable_count = 0
            free_vram = cur_free

        print(f"{label} VRAM still settling after {max_wait}s "
              f"(current {free_vram:.0f} MiB, peak {peak_free:.0f})",
              file=sys.stderr, flush=True)
        if min_free_mb and free_vram < min_free_mb:
            print(f"{label} WARNING: VRAM ({free_vram:.0f} MiB) below required "
                  f"{min_free_mb} MiB — OOM risk high!",
                  file=sys.stderr, flush=True)
        return free_vram
    except Exception:
        print(f"{label} torch not available, sleep 3s for GPU cleanup",
              file=sys.stderr, flush=True)
        time.sleep(3)
        return 0


def _wait_for_llama_ready(port=8080, timeout=180, label="[LLAMA]"):
    """
    三阶段等待 llama-server 完全就绪：
    1. 端口打开（最多 timeout 秒）
    2. /health 返回 200（最多 30s）
    3. /completion 返回有效响应（最多 60s）

    返回 True 表示就绪，False 表示超时。
    """
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout

    # 阶段 1: 端口打开
    while time.time() < deadline:
        if _port_open("127.0.0.1", port, timeout=1):
            print(f"{label} 端口 {port} 已打开", file=sys.stderr, flush=True)
            break
        time.sleep(0.5)
    else:
        print(f"{label} 超时：端口 {port} 在 {timeout}s 内未打开",
              file=sys.stderr, flush=True)
        return False

    # 阶段 2: /health 端点
    health_deadline = min(time.time() + 30, deadline + 10)
    health_ok = False
    while time.time() < health_deadline:
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    print(f"{label} /health 200 OK", file=sys.stderr, flush=True)
                    health_ok = True
                    break
        except Exception:
            pass
        time.sleep(0.5)
    if not health_ok:
        print(f"{label} /health 端点超时", file=sys.stderr, flush=True)
        return False

    # 阶段 3: /completion 功能验证
    comp_deadline = min(time.time() + 60, deadline + 10)
    import json as _json
    test_payload = _json.dumps({
        "prompt": "hi",
        "n_predict": 1,
        "temperature": 0,
        "cache_prompt": False,
    }).encode("utf-8")
    while time.time() < comp_deadline:
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/completion",
                data=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer 123456",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    body = resp.read()
                    data = _json.loads(body)
                    if data.get("content") or data.get("stop"):
                        print(f"{label} /completion 验证通过 — 就绪 ✓",
                              file=sys.stderr, flush=True)
                        return True
        except Exception:
            pass
        time.sleep(0.5)

    print(f"{label} 警告：/completion 在超时前未响应，但端口可用，允许尝试",
          file=sys.stderr, flush=True)
    return True  # 至少端口和 /health 都过了


# ---- 文件锁 ----

def acquire_lock(lock_file, label="skill"):
    """
    获取文件锁，防止同一 skill 重复执行。

    返回 (pid_str, exe_path)；如果已有实例在运行则返回 (None, None)。
    """
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                data = json.loads(f.read().strip())
            old_pid = data.get('pid')
            old_exe = data.get('exe', '')
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {old_pid}', '/NH'],
                capture_output=True, text=True, timeout=5
            )
            if (old_pid and str(old_pid) in result.stdout
                    and 'python.exe' in result.stdout):
                if old_exe and old_exe in result.stdout:
                    print(f"[LOCK] 检测到正在运行的 {label} (PID={old_pid})，跳过",
                          file=sys.stderr, flush=True)
                    return None, None
            print("[LOCK] 旧锁文件残留（进程已死），清理中...",
                  file=sys.stderr, flush=True)
            os.remove(lock_file)
        except (ValueError, OSError, json.JSONDecodeError,
                subprocess.TimeoutExpired):
            print("[LOCK] 旧锁文件残留（进程已死），清理中...",
                  file=sys.stderr, flush=True)
            try:
                os.remove(lock_file)
            except FileNotFoundError:
                pass

    pid = os.getpid()
    exe_path = sys.executable
    lock_data = json.dumps({'pid': pid, 'exe': exe_path})
    os.makedirs(os.path.dirname(lock_file), exist_ok=True)
    with open(lock_file, 'w') as f:
        f.write(lock_data)
    print(f"[LOCK] 已获取锁 (PID={pid}, exe={exe_path})",
          file=sys.stderr, flush=True)
    return str(pid), exe_path


def release_lock(lock_file):
    """释放锁文件"""
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
            print("[LOCK] 已释放锁", file=sys.stderr, flush=True)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[LOCK] 释放锁异常: {e}", file=sys.stderr, flush=True)


# ---- Llama Server 启停 ----

def stop_llama(port=8080, wait_vram_stable=True):
    """
    停止 llama-server（如果正在运行）。

    先尝试 HTTP /shutdown 优雅关闭，失败后 taskkill 强杀。
    wait_vram_stable=True 时等待 CUDA VRAM 完全释放后再返回。

    返回 True 表示已停止（或本来就没运行）。
    """
    print("[LLAMA] 检查 llama-server 状态...", file=sys.stderr, flush=True)

    if not _port_open("127.0.0.1", port, timeout=1):
        print("[LLAMA] llama-server 未运行，跳过", file=sys.stderr, flush=True)
        return False

    print("[LLAMA] 停止 llama-server...", file=sys.stderr, flush=True)
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{port}/shutdown", timeout=2)
        print("[LLAMA] 已发送优雅关闭请求", file=sys.stderr, flush=True)
    except Exception:
        print("[LLAMA] HTTP 关闭失败，使用 taskkill", file=sys.stderr, flush=True)
        subprocess.run(
            ["taskkill", "/f", "/im", "llama-server.exe"],
            capture_output=True, text=False
        )

    # 等待端口释放
    for i in range(30):
        if not _port_open("127.0.0.1", port, timeout=1):
            print(f"[LLAMA] 端口 {port} 已释放 ({i + 1}s)",
                  file=sys.stderr, flush=True)
            break
        time.sleep(0.5)
    else:
        print(f"[LLAMA] 警告：端口 {port} 仍未释放，继续执行",
              file=sys.stderr, flush=True)

    # CUDA VRAM 稳定检测 — 仅记录，不做硬阻塞
    # --no-mmap 需要 ~7.5GB，8GB 卡上窗口极窄，靠 llama 自己的 -fit 自适应
    if wait_vram_stable:
        _wait_for_vram_stable(min_free_mb=None, max_wait=10)

    return True


def start_llama(port=8080, exe_path=None, model_path=None,
                log_dir=None, timeout=180):
    """
    启动 llama-server 并等待就绪。

    参数由调用方传入（路径因部署而异）。
    返回 True 表示启动成功，False 表示失败。
    """
    print("[LLAMA] 启动 llama-server...", file=sys.stderr, flush=True)

    # VRAM 激进清理 — ComfyUI 推理后 tensor 可能还被驱动持有
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            import gc
            gc.collect()
            time.sleep(3)  # 等驱动回收
            torch.cuda.empty_cache()
            gc.collect()
            time.sleep(2)
            free = torch.cuda.mem_get_info()[0] / (1024 ** 2)
            total = torch.cuda.mem_get_info()[1] / (1024 ** 2)
            print(f"[LLAMA] VRAM: {free:.0f} MiB free / {total:.0f} MiB total",
                  file=sys.stderr, flush=True)
    except Exception:
        pass  # torch 不可用时跳过

    # 先确保旧进程被清理干净（端口可能未完全释放）
    if _port_open("127.0.0.1", port, timeout=1):
        print("[LLAMA] 端口仍被占用，强制清理...", file=sys.stderr, flush=True)
        subprocess.run(
            ["taskkill", "/f", "/im", "llama-server.exe"],
            capture_output=True, text=False
        )
        for i in range(10):
            if not _port_open("127.0.0.1", port, timeout=1):
                print(f"[LLAMA] 端口已释放 ({i + 1}s)",
                      file=sys.stderr, flush=True)
                break
            time.sleep(0.5)

    # VRAM 自适应 — 如果自由VRAM < 7GB，减ngl到30
    try:
        ngl = 41
        import torch
        if torch.cuda.is_available():
            free = torch.cuda.mem_get_info()[0] / (1024 ** 2)
            if free < 7000:
                ngl = 30
                print(f"[LLAMA] VRAM 仅 {free:.0f} MiB，降 ngl 41→30",
                      file=sys.stderr, flush=True)
    except Exception:
        ngl = 41

    args = [
        exe_path or "llama-server.exe",
        "-m", model_path or "",
        "-c", "120000",
        "--flash-attn", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-ngl", str(ngl),
        "--cpu-moe",
        "--cpu-mask", "0xFFFFFFFF",
        "--batch-size", "4096",
        "--ubatch-size", "2048",
        "--threads", "24",
        "--api-key", "123456",
        "-rea", "off",
        "--jinja",
        "--cache-ram", "5000",
        "--parallel", "1",
        "--kv-unified",
        "--no-mmap",
        "--no-warmup",
    ]

    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    proc = subprocess.Popen(
        args,
        stdout=(open(os.path.join(log_dir, "llama-out.log"), "ab")
                if log_dir else subprocess.DEVNULL),
        stderr=(open(os.path.join(log_dir, "llama-err.log"), "ab")
                if log_dir else subprocess.DEVNULL),
    )

    print(f"[LLAMA] 已启动，PID={proc.pid}，等待端口 {port}...",
          file=sys.stderr, flush=True)
    return _wait_for_llama_ready(port=port, timeout=timeout)


# ---- 硬超时守卫 ----

class TimeoutGuard:
    """子进程硬超时守卫：超时后强杀自身，清理锁"""

    def __init__(self, timeout_sec, lock_file=None):
        self.timeout_sec = timeout_sec
        self.lock_file = lock_file
        self._timer = None

    def __enter__(self):
        self._timer = threading.Timer(self.timeout_sec, self._timeout_exit)
        self._timer.daemon = True
        self._timer.start()
        return self

    def __exit__(self, *args):
        if self._timer:
            self._timer.cancel()

    def _timeout_exit(self):
        print(f"[FATAL] 硬超时 {self.timeout_sec}s，强制退出防止死锁",
              file=sys.stderr, flush=True)
        if self.lock_file:
            release_lock(self.lock_file)
        subprocess.run(
            ["taskkill", "/f", "/t", "/pid", str(os.getpid())],
            capture_output=True, text=True, timeout=3
        )
        os._exit(2)


# ---- atexit / signal 清理钩子 ----

_cleanup_lock_file = None
_cleanup_restart_script = None
_cleanup_llama_port = None
_lock_released = False


def _cleanup_lock():
    global _lock_released
    if not _lock_released:
        _lock_released = True
        if _cleanup_lock_file:
            release_lock(_cleanup_lock_file)


def _atexit_handler():
    _cleanup_lock()
    # 确保 llama-server 被重启（如果之前停了）
    if _cleanup_llama_port and _cleanup_restart_script:
        try:
            if not _port_open("127.0.0.1", _cleanup_llama_port, timeout=0.5):
                subprocess.Popen(
                    ["powershell", "-Command",
                     f"Start-Process -WindowStyle Hidden -FilePath '{_cleanup_restart_script}'"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        except Exception:
            pass


def _signal_handler(signum, frame):
    _cleanup_lock()
    sys.exit(1)


def register_cleanup_handlers(lock_file, llama_port=None,
                              restart_script=None):
    """
    注册 atexit 和 signal 钩子，确保进程退出时：
    1. 释放文件锁
    2. 重启 llama-server（如果端口未占用）

    参数：
        lock_file: 锁文件路径
        llama_port: llama-server 端口（用于检测是否需要重启）
        restart_script: llama 重启脚本路径（.ps1）
    """
    global _cleanup_lock_file, _cleanup_restart_script
    global _cleanup_llama_port, _lock_released
    _cleanup_lock_file = lock_file
    _cleanup_restart_script = restart_script
    _cleanup_llama_port = llama_port
    _lock_released = False

    # 注册 atexit
    atexit.register(_atexit_handler)

    # 注册信号处理
    try:
        signal.signal(signal.SIGINT, _signal_handler)
    except (OSError, ValueError):
        pass
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
    except (OSError, ValueError):
        pass

#!/usr/bin/env python3
"""
ComfyUI 文生图调用脚本 — 直接加载模型推理，不走 WebUI HTTP API。
用法: python comfyui_call.py "正prompt" "负prompt" [seed] [宽] [高] [步数] [CFG] [模型名]
输出: 标准输出打印生成的 PNG 文件路径

可用模型:
  WAI-Nsfw-Illustrious-17.safetensors  (6.5GB, 训练至 2025-05, 层次分明)
  miaomiaoHarem_v20.safetensors        (6.5GB, 训练至 2026-01, 偏油但库新)
"""
import sys
import os
import time
import random
import json
import atexit
import signal
import threading
import numpy as np
import subprocess
import socket

# ========== 路径配置 ==========
COMFYUI_ROOT = r"E:\comfyui\ComfyUI-aki-v3\ComfyUI"
PYTHON_PATH = r"E:\comfyui\ComfyUI-aki-v3\python"
CHECKPOINTS_DIR = r"E:\comfyui\ComfyUI-aki-v3\ComfyUI\models\checkpoints"
OUTPUT_DIR = r"C:\Users\TK\.openclaw\workspace\comfyui_output"

# ========== LLama Server 配置 ==========
LLAMA_LOG_DIR = r"C:\Users\TK\Desktop\vllm\restart-logs"
LLAMA_EXE_PATH = r"C:\Users\TK\Desktop\vllm\llama-b9222-bin-win-cuda-12.4-x64\llama-server.exe"
LLAMA_MODEL_PATH = r"C:\Users\TK\Desktop\vllm\models\Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf"
RESTART_SCRIPT = r"C:\Users\TK\Desktop\vllm\restart-llama.ps1"
LLAMA_PORT = 8080

# ========== 硬超时（防止子进程卡死不退出，导致 gateway session 锁死） ==========
HARD_TIMEOUT = 600  # 秒，超过这个时间强制退出
_deadline = None

import re

def slugify(text, max_len=30):
    """从文本提取安全文件名标签（英文/数字/中文保留）"""
    # 保留中英文、数字、空格，其余替换为空格
    cleaned = re.sub(r'[^\w\u4e00-\u9fff ]', ' ', text, flags=re.ASCII)
    # 合并空格
    cleaned = re.sub(r'\s+', '_', cleaned).strip('_')
    # 截断
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip('_')
    return cleaned or 'untitled'

# ========== 默认参数 ==========
# 可用模型:
#   WAI-Nsfw-Illustrious-17.safetensors  (6.5GB, 训练至 2025-05, 层次分明, 推荐)
#   miaomiaoHarem_v20.safetensors        (6.5GB, 训练至 2026-01, 偏油但库新)
# 第8个命令行参数指定模型名，不传则用下面默认值
DEFAULT_CKPT = "WAI-Nsfw-Illustrious-17.safetensors"
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 1500
DEFAULT_STEPS = 30
DEFAULT_CFG = 6.0
DEFAULT_SAMPLER = "dpmpp_2s_ancestral"
DEFAULT_SCHEDULER = "karras"

# ========== 防重复执行 ==========
# 使用 lock 文件防止并发/重复调用（如 exec 超时后 agent 重试导致跑两次）
LOCK_FILE = os.path.join(OUTPUT_DIR, ".comfyui_running.lock")
# 上一次生成记录（防止重复推送同一张图）
LAST_OUTPUT_FILE = os.path.join(OUTPUT_DIR, ".comfyui_last_output.txt")


# ==================== Llama Server 管理 ====================

def acquire_lock():
    """获取文件锁，防止重复执行。返回 lock_pid 和 python_exe 路径。"""
    # 如果 lock 文件存在且进程还活着，说明上次没干净退出
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                data = json.loads(f.read().strip())
            old_pid = data.get('pid')
            old_exe = data.get('exe', '')
            # Windows 下检查进程是否还存活
            result = subprocess.run(['tasklist', '/FI', f'PID eq {old_pid}', '/NH'], capture_output=True, text=True, timeout=5)
            if old_pid and str(old_pid) in result.stdout and 'python.exe' in result.stdout:
                # 确认是同一个 comfyui python 进程
                if old_exe and old_exe in result.stdout:
                    print(f"[LOCK] 检测到正在运行的 comfyui (PID={old_pid})，跳过", file=sys.stderr, flush=True)
                    return None, None
            # 进程已死，lock 文件残留，清理
            print("[LOCK] 旧锁文件残留（进程已死），清理中...", file=sys.stderr, flush=True)
            os.remove(LOCK_FILE)
        except (ValueError, OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
            print("[LOCK] 旧锁文件残留（进程已死），清理中...", file=sys.stderr, flush=True)
            try:
                os.remove(LOCK_FILE)
            except FileNotFoundError:
                pass

    # 创建锁文件，记录 python.exe 路径用于精确匹配
    pid = os.getpid()
    exe_path = sys.executable
    lock_data = json.dumps({'pid': pid, 'exe': exe_path})
    with open(LOCK_FILE, 'w') as f:
        f.write(lock_data)
    print(f"[LOCK] 已获取锁 (PID={pid}, exe={exe_path})", file=sys.stderr, flush=True)
    return str(pid), exe_path


def release_lock(pid=None):
    """释放锁文件。直接删除（防止进程被强杀时锁残留）"""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            print("[LOCK] 已释放锁", file=sys.stderr, flush=True)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[LOCK] 释放锁异常: {e}", file=sys.stderr, flush=True)


def _port_open(host, port, timeout=2):
    """检测指定端口是否开启"""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


def stop_llama():
    """停止 llama-server（如果正在运行）"""
    print("[LLAMA] 检查 llama-server 状态...", file=sys.stderr, flush=True)

    # 检测端口
    if not _port_open("127.0.0.1", LLAMA_PORT, timeout=1):
        print("[LLAMA] llama-server 未运行，跳过", file=sys.stderr, flush=True)
        return False

    print("[LLAMA] 停止 llama-server...", file=sys.stderr, flush=True)
    # 先尝试优雅关闭（发送 shutdown 请求），再强杀
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{LLAMA_PORT}/shutdown", timeout=2)
        print("[LLAMA] 已发送优雅关闭请求", file=sys.stderr, flush=True)
    except Exception:
        print("[LLAMA] HTTP 关闭失败，使用 taskkill", file=sys.stderr, flush=True)
        subprocess.run(
            ["taskkill", "/f", "/im", "llama-server.exe"],
            capture_output=True, text=False
        )

    # 等待端口释放
    for i in range(30):
        if not _port_open("127.0.0.1", LLAMA_PORT, timeout=1):
            print(f"[LLAMA] 端口 {LLAMA_PORT} 已释放 ({i+1}s)", file=sys.stderr, flush=True)
            return True
        time.sleep(0.5)

    print(f"[LLAMA] 警告：端口 {LLAMA_PORT} 仍未释放，继续执行", file=sys.stderr, flush=True)
    return True


def _wait_for_llama_ready(host, port, timeout=180):
    """等待 llama-server 端口打开 + HTTP 健康检查通过"""
    import urllib.request
    
    # 阶段1: 等待端口打开
    for i in range(timeout):
        if _port_open("127.0.0.1", port, timeout=2):
            print(f"[LLAMA] 端口 {port} 已打开 ({i+1}s)", file=sys.stderr, flush=True)
            break
        if i % 10 == 9:
            print(f"[LLAMA] 等待端口中... ({i+1}s)", file=sys.stderr, flush=True)
    else:
        print(f"[LLAMA] 警告：{port} 端口未在 {timeout}s 内打开", file=sys.stderr, flush=True)
        return False
    
    # 阶段2: HTTP 健康检查（发送一个 /health 请求确认模型已加载）
    # 注意：llama-server 的 /health 端点在模型加载完成后才返回 200
    # 如果端口打开了但模型还在加载，/health 会返回 503
    print("[LLAMA] 等待模型加载（HTTP 健康检查）...", file=sys.stderr, flush=True)
    for i in range(timeout):
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5)
            if resp.status == 200:
                print(f"[LLAMA] llama-server 完全就绪（模型已加载）！({i+1}s)", file=sys.stderr, flush=True)
                return True
        except Exception:
            pass
        if i % 5 == 4:
            print(f"[LLAMA] 模型加载中... ({i+1}s)", file=sys.stderr, flush=True)
    
    # 阶段3: 发一个真实的 completion 请求确认模型能正常响应
    # /health 200 不一定意味着模型已加载完毕，需要实际请求验证
    print("[LLAMA] 验证模型可用（发送测试请求）...", file=sys.stderr, flush=True)
    import json as _json
    test_payload = _json.dumps({
        "prompt": "hi",
        "n_predict": 1,
        "temperature": 0,
        "cache_prompt": False
    }).encode('utf-8')
    for i in range(min(timeout, 60)):
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/completion",
                data=test_payload,
                headers={"Content-Type": "application/json", "Authorization": "Bearer 123456"}
            )
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.status == 200:
                body = resp.read()
                data = _json.loads(body)
                if data.get("content") or data.get("stop"):
                    print(f"[LLAMA] 模型完全就绪（completion 验证通过）！({i+1}s)", file=sys.stderr, flush=True)
                    return True
        except Exception:
            pass
        if i % 5 == 4:
            print(f"[LLAMA] 等待模型可生成... ({i+1}s)", file=sys.stderr, flush=True)
    
    print(f"[LLAMA] 警告：/completion 未在 {min(timeout, 60)}s 内响应", file=sys.stderr, flush=True)
    return True


def start_llama():
    """重启 llama-server（与 restart-llama.ps1 相同的参数）"""
    print("[LLAMA] 启动 llama-server...", file=sys.stderr, flush=True)

    # 先确保旧进程被清理干净（端口可能未完全释放）
    if _port_open("127.0.0.1", LLAMA_PORT, timeout=1):
        print("[LLAMA] 端口仍被占用，强制清理...", file=sys.stderr, flush=True)
        subprocess.run(["taskkill", "/f", "/im", "llama-server.exe"], capture_output=True, text=False)
        for i in range(10):
            if not _port_open("127.0.0.1", LLAMA_PORT, timeout=1):
                print(f"[LLAMA] 端口已释放 ({i+1}s)", file=sys.stderr, flush=True)
                break
            time.sleep(0.5)

    args = [
        LLAMA_EXE_PATH,
        "-m", LLAMA_MODEL_PATH,
        "-c", "120000",
        "--flash-attn", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-ngl", "41",
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

    os.makedirs(LLAMA_LOG_DIR, exist_ok=True)

    proc = subprocess.Popen(
        args,
        stdout=open(os.path.join(LLAMA_LOG_DIR, "llama-out.log"), "ab"),
        stderr=open(os.path.join(LLAMA_LOG_DIR, "llama-err.log"), "ab"),
    )

    print(f"[LLAMA] 已启动，PID={proc.pid}，等待端口 {LLAMA_PORT}...", file=sys.stderr, flush=True)

    # 使用新的健康检查函数（端口打开 + HTTP /health 通过）
    return _wait_for_llama_ready("127.0.0.1", LLAMA_PORT, timeout=180)


def safe_load_safetensors(ckpt_path):
    """
    手动加载 safetensors 文件，绕过 cu130 在 RTX 5070 (Blackwell) 上
    safetensors.torch.load_file 的 torch.storage 访问崩溃 bug。
    """
    import torch

    with open(ckpt_path, 'rb') as f:
        header_len = int.from_bytes(f.read(8), 'little')
        header = json.loads(f.read(header_len))
        data_start = 8 + header_len

        dtype_map = {
            'F32': np.float32, 'F16': np.float16, 'F64': np.float64,
            'I32': np.int32, 'I64': np.int64, 'I8': np.int8, 'I16': np.int16,
            'U8': np.uint8, 'U16': np.uint16, 'U32': np.uint32, 'U64': np.uint64,
            'BF16': np.float16,
        }

        state_dict = {}
        for key, info in header.items():
            start, end = info['data_offsets']
            f.seek(data_start + start)
            raw = f.read(end - start)
            dt = dtype_map.get(info['dtype'], np.float32)
            arr = np.frombuffer(raw, dtype=dt).reshape(info['shape'])
            state_dict[key] = torch.from_numpy(arr.copy())

    return state_dict


def run_txt2img(positive_prompt, negative_prompt, seed, width, height, steps, cfg, ckpt_name, manage_llama=True):
    """
    主推理函数
    manage_llama: 自动管理 llama-server（停→跑图→启），默认开启
    
    manage_llama=True（默认）：停 llama-server 腾显存，跑图更快但对话会中断
    manage_llama=False：不停 llama-server，对话不中断，但需要更多显存
    """
    import torch

    # 停掉 llama-server 腾显存
    if manage_llama:
        stop_llama()

    # 导入 ComfyUI 路径
    sys.path.insert(0, COMFYUI_ROOT)
    sys.path.insert(0, PYTHON_PATH)
    os.environ["COMFYUI_PATH"] = COMFYUI_ROOT
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    os.environ["MIMALLOC_PURGE_DELAY"] = "0"

    # ComfyUI 初始化（需在 import 前）
    import folder_paths
    import comfy.options
    comfy.options.enable_args_parsing()

    t0 = time.time()

    # ---------- 1. 加载模型 ----------
    ckpt_path = os.path.join(CHECKPOINTS_DIR, ckpt_name)
    if not os.path.exists(ckpt_path):
        for root, dirs, files in os.walk(CHECKPOINTS_DIR):
            if ckpt_name in files:
                ckpt_path = os.path.join(root, ckpt_name)
                break
    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"找不到模型: {ckpt_name}")

    from comfy.sd import load_state_dict_guess_config
    from comfy import model_management

    print(f"读取模型: {os.path.basename(ckpt_path)} ({os.path.getsize(ckpt_path)/1024**3:.1f}GB)", file=sys.stderr, flush=True)
    state_dict = safe_load_safetensors(ckpt_path)
    print(f"模型加载完成 ({time.time()-t0:.1f}s)", file=sys.stderr, flush=True)

    result = load_state_dict_guess_config(sd=state_dict)
    model, clip, vae = result[0], result[1], result[2]
    print(f"模型导入完成 ({time.time()-t0:.1f}s)", file=sys.stderr, flush=True)

    # ---------- 2. 文本编码 ----------
    from nodes import CLIPTextEncode
    dev = model_management.get_torch_device()

    pos_node = CLIPTextEncode()
    pos_out = pos_node.encode(text=positive_prompt, clip=clip)[0]
    neg_node = CLIPTextEncode()
    neg_out = neg_node.encode(text=negative_prompt, clip=clip)[0]
    print(f"文本编码完成 ({time.time()-t0:.1f}s)", file=sys.stderr, flush=True)

    # ---------- 3. 采样 ----------
    from nodes import common_ksampler

    latent = {"samples": torch.zeros((1, 4, height // 8, width // 8), device=dev)}
    samples = common_ksampler(
        model, seed=seed, steps=steps, cfg=cfg,
        sampler_name=DEFAULT_SAMPLER,
        scheduler=DEFAULT_SCHEDULER,
        positive=pos_out, negative=neg_out,
        latent=latent, denoise=1.0,
    )
    print(f"采样完成 ({time.time()-t0:.1f}s)", file=sys.stderr, flush=True)

    # ---------- 4. VAE 解码 ----------
    try:
        from nodes import VAEDecode
        vd = VAEDecode()
        images = vd.decode(vae, samples[0])[0]
    except Exception:
        print("VAE decode 失败，尝试 tiled decode...", file=sys.stderr, flush=True)
        vae.vae_dtype = torch.float32
        images = vae.decode_tiled(samples[0]["samples"], tile_x=64, tile_y=64, overlap=16)
    print(f"VAE解码完成 ({time.time()-t0:.1f}s), shape={images.shape}", file=sys.stderr, flush=True)

    # ---------- 5. 保存 ----------
    from PIL import Image

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # 从 prompt 提取标签用于文件名
    tag = slugify(positive_prompt.split(',')[0])
    fname = f"comfyui_{tag}_{seed}.png"
    out_path = os.path.join(OUTPUT_DIR, fname)

    for img in images:
        img = img.detach().cpu().numpy()
        img = np.clip(img * 255, 0, 255).astype(np.uint8)
        # CHW → HWC
        if img.shape[0] == 3 or img.shape[0] == 1:
            img = img.transpose(1, 2, 0)
        if img.shape[2] == 1:
            img = img.squeeze(2)
        Image.fromarray(img).save(out_path)
        break  # 只取第一张

    # 写入上一次输出记录（用于防重复推送）
    with open(LAST_OUTPUT_FILE, 'w') as f:
        f.write(out_path)

    total = time.time() - t0
    print("=" * 60, file=sys.stderr, flush=True)
    print(f"完成! 总耗时: {total:.1f}s", file=sys.stderr, flush=True)
    print(f"输出: {out_path}", file=sys.stderr, flush=True)
    print("=" * 60, file=sys.stderr, flush=True)

    # 先重启 llama-server，等它完全就绪再输出结果
    # 这样 subagent announce 回主 session 时，llama 已经在线
    # 主 session 才能调用 LLM 组装消息推送给用户
    if manage_llama:
        sys.stderr.flush()
        start_llama()
        print(f"[LLAMA] 已就绪，继续输出结果", file=sys.stderr, flush=True)

    # 标准输出返回路径（现在 llama 已经在线，主 session 能处理 announce）
    sys.stdout.write(out_path + '\n')
    sys.stdout.flush()


# ========== 全局清理（防止进程被强杀时锁残留） ==========
# ========== 全局防护：硬超时 + atexit + 信号 ==========
_guard_armed = False

class TimeoutGuard:
    """子进程硬超时守卫：超时后强杀自身，清理锁"""
    def __init__(self, timeout_sec):
        self.timeout_sec = timeout_sec
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
        print(f"[FATAL] 硬超时 {self.timeout_sec}s，强制退出防止死锁", file=sys.stderr, flush=True)
        release_lock()
        # 尝试 taskkill 自己（包括子进程树）
        subprocess.run(["taskkill", "/f", "/t", "/pid", str(os.getpid())],
                       capture_output=True, text=True, timeout=3)
        os._exit(2)

_lock_released = False

def _cleanup_lock():
    """atexit 回调：确保锁文件被清理"""
    global _lock_released
    if not _lock_released:
        _lock_released = True
        release_lock()

# 注册 atexit
def _atexit_handler():
    _cleanup_lock()
    # 确保 llama-server 被重启（如果之前停了）
    try:
        if not _port_open("127.0.0.1", LLAMA_PORT, timeout=0.5):
            # 用 nohup 方式启动 - 不给 gateway 留僵尸
            subprocess.Popen(
                ["powershell", "-Command", f"Start-Process -WindowStyle Hidden -FilePath '{RESTART_SCRIPT}'"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    except Exception:
        pass

atexit.register(_atexit_handler)

# 注册信号处理
def _signal_handler(signum, frame):
    _cleanup_lock()
    sys.exit(1)

try:
    signal.signal(signal.SIGINT, _signal_handler)
except (OSError, ValueError):
    pass
try:
    signal.signal(signal.SIGTERM, _signal_handler)
except (OSError, ValueError):
    pass


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"用法: python {sys.argv[0]} \"正prompt\" \"负prompt\" [seed] [宽] [高] [步数] [CFG] [模型名] [--no-manage-llama]", file=sys.stderr)
        sys.exit(1)

    positive_prompt = sys.argv[1]
    negative_prompt = sys.argv[2]
    
    # 解析 --no-manage-llama 标志
    no_manage_llama = '--no-manage-llama' in sys.argv
    
    # 过滤掉 --no-manage-llama 后的位置参数
    clean_args = [a for a in sys.argv if a != '--no-manage-llama']
    seed = int(clean_args[3]) if len(clean_args) > 3 else random.randint(0, 2**63 - 1)
    width = int(clean_args[4]) if len(clean_args) > 4 else DEFAULT_WIDTH
    height = int(clean_args[5]) if len(clean_args) > 5 else DEFAULT_HEIGHT
    steps = int(clean_args[6]) if len(clean_args) > 6 else DEFAULT_STEPS
    cfg = float(clean_args[7]) if len(clean_args) > 7 else DEFAULT_CFG
    ckpt_name = clean_args[8] if len(clean_args) > 8 else DEFAULT_CKPT

    # 获取锁（防止并发/超时重试导致跑两次）
    lock_pid, lock_exe = acquire_lock()
    if lock_pid is None:
        print("[ERROR] 已有 comfyui 实例在运行，跳过本次调用", file=sys.stderr)
        sys.exit(0)

    try:
        manage_llama = not no_manage_llama
        if no_manage_llama:
            print("[LLAMA] 不停 llama-server，保持对话连续", file=sys.stderr, flush=True)
        
        # 硬超时保护：子进程最多跑 HARD_TIMEOUT 秒，超时自动强杀
        with TimeoutGuard(HARD_TIMEOUT):
            run_txt2img(positive_prompt, negative_prompt, seed, width, height, steps, cfg, ckpt_name, manage_llama=manage_llama)
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        # 异常退出也要保证 llama 被重启
        try:
            if manage_llama and not _port_open("127.0.0.1", LLAMA_PORT, timeout=0.5):
                subprocess.Popen(
                    ["powershell", "-Command", f"Start-Process -WindowStyle Hidden -FilePath '{RESTART_SCRIPT}'"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        except Exception:
            pass
        sys.exit(1)
    finally:
        release_lock()

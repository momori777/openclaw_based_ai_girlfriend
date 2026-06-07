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
import numpy as np
import subprocess

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


# ==================== Llama Server 管理（共享模块） ====================

# 导入共享 lifecycle 模块
_pkg_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from skills.shared.llama_lifecycle import (
    acquire_lock, release_lock,
    stop_llama, start_llama,
    TimeoutGuard, register_cleanup_handlers,
    _port_open,
)

# 注册 atexit/signal 清理钩子（共享模块）
register_cleanup_handlers(
    lock_file=LOCK_FILE,
    llama_port=LLAMA_PORT,
    restart_script=RESTART_SCRIPT,
)


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
        stop_llama(port=LLAMA_PORT)

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
    # 从 prompt 提取标签 + 时间戳作为文件名
    from datetime import datetime
    tag = slugify(positive_prompt.split(',')[0])
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    fname = f"comfyui_{tag}_{ts}.png"
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
        start_llama(
            port=LLAMA_PORT,
            exe_path=LLAMA_EXE_PATH,
            model_path=LLAMA_MODEL_PATH,
            log_dir=LLAMA_LOG_DIR,
            timeout=180,
        )
        print(f"[LLAMA] 已就绪，继续输出结果", file=sys.stderr, flush=True)

    # 标准输出返回路径（现在 llama 已经在线，主 session 能处理 announce）
    sys.stdout.write(out_path + '\n')
    sys.stdout.flush()


# ========== (cleanup handlers now managed by skills.shared.llama_lifecycle) ==========


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
    lock_pid, lock_exe = acquire_lock(LOCK_FILE, label="comfyui")
    if lock_pid is None:
        print("[ERROR] 已有 comfyui 实例在运行，跳过本次调用", file=sys.stderr)
        sys.exit(0)

    try:
        manage_llama = not no_manage_llama
        if no_manage_llama:
            print("[LLAMA] 不停 llama-server，保持对话连续", file=sys.stderr, flush=True)
        
        # 硬超时保护：子进程最多跑 HARD_TIMEOUT 秒，超时自动强杀
        with TimeoutGuard(HARD_TIMEOUT, lock_file=LOCK_FILE):
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
        release_lock(LOCK_FILE)

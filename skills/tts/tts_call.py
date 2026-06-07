#!/usr/bin/env python3
"""
GPT-SoVITS TTS 调用脚本 — 子进程自动化流程
用法: python tts_call.py "目标文本" "语言代码" [情绪模式]
语言代码: zh=中文, ja=日文, en=英文
情绪模式: casual=日常温柔, tsundere=傲娇强势, romantic=深情, long=长句稳定, random=随机
输出: 标准输出打印生成的 wav 文件路径

自动化流程（与 ComfyUI 子进程一致）：
1. 获取文件锁防止并发
2. 停 llama-server 腾显存
3. 执行 TTS 推理
4. 重启 llama-server 等待就绪
5. 输出结果（现在 llama 已在线，announce 不会 timeout）
6. 释放锁 + atexit/signal 清理
"""
import sys
import os
import time
import random
import json
import atexit
import signal
import numpy as np
import scipy.io.wavfile
import subprocess
import socket
import threading

# Change to WebUI directory
WEBUI_DIR = r"C:\Users\TK\Desktop\vllm\GPT-SoVITS-v2pro-20250604-nvidia50"
os.chdir(WEBUI_DIR)
sys.path.insert(0, WEBUI_DIR)

# ========== 路径配置 ==========
OUTPUT_DIR = r"C:\Users\TK\.openclaw\workspace\qqbot\audio"
LOCK_FILE = os.path.join(OUTPUT_DIR, ".tts_running.lock")

# ========== Llama Server 配置 ==========
LLAMA_LOG_DIR = r"C:\Users\TK\Desktop\vllm\restart-logs"
LLAMA_EXE_PATH = r"C:\Users\TK\Desktop\vllm\llama-b9222-bin-win-cuda-12.4-x64\llama-server.exe"
LLAMA_MODEL_PATH = r"C:\Users\TK\Desktop\vllm\models\Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Compact.gguf"
RESTART_SCRIPT = r"C:\Users\TK\Desktop\vllm\restart-llama.ps1"
LLAMA_PORT = 8080

# ========== 硬超时（防止子进程卡死不退出，导致 gateway session 锁死） ==========
HARD_TIMEOUT = 300  # 秒，超过这个时间强制退出

import re

def slugify(text, max_len=20):
    """从文本提取安全文件名标签（保留中英文/数字）"""
    cleaned = re.sub(r'[^\w\u4e00-\u9fff ]', ' ', text, flags=re.ASCII)
    cleaned = re.sub(r'\s+', '_', cleaned).strip('_')
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip('_')
    return cleaned or 'untitled'


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
                # 确认是同一个 python 进程
                if old_exe and old_exe in result.stdout:
                    print(f"[LOCK] 检测到正在运行的 tts (PID={old_pid})，跳过", file=sys.stderr, flush=True)
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
    """检测指定端口是否开启（使用共享模块）"""
    # 添加项目根目录到 sys.path 以便导入 shared 模块
    _scripts_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    from skills.shared.llama_utils import port_open
    return port_open(host, port, timeout)


def stop_llama():
    """停止 llama-server（如果正在运行）"""
    print("[LLAMA] 检查 llama-server 状态...", file=sys.stderr, flush=True)

    # 检测端口（使用共享模块）
    from skills.shared.llama_utils import port_open
    if not port_open("127.0.0.1", LLAMA_PORT, timeout=1):
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
    from skills.shared.llama_utils import port_open
    for i in range(30):
        if not port_open("127.0.0.1", LLAMA_PORT, timeout=1):
            print(f"[LLAMA] 端口 {LLAMA_PORT} 已释放 ({i+1}s)", file=sys.stderr, flush=True)
            return True
        time.sleep(0.5)

    print(f"[LLAMA] 警告：端口 {LLAMA_PORT} 仍未释放，继续执行", file=sys.stderr, flush=True)
    return True


def _wait_for_llama_ready(host, port, timeout=180):
    """等待 llama-server 完全就绪（使用共享模块）"""
    # 添加项目根目录到 sys.path 以便导入 shared 模块
    _scripts_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    from skills.shared.llama_utils import wait_for_llama_ready
    return wait_for_llama_ready(port=port, timeout=timeout, log=lambda msg: print(msg, file=sys.stderr, flush=True))


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

    # 使用两阶段健康检查（端口打开 + HTTP /health 200）
    return _wait_for_llama_ready("127.0.0.1", LLAMA_PORT, timeout=180)


# ========== TimeoutGuard 类（与 ComfyUI 一致） ==========
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


# 参考音频目录（相对于脚本所在目录）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(_SCRIPT_DIR, "ref_wavs")

# 14个预筛选的参考音频，按情绪分类
REF_WAVES = {
    "casual": [
        {"path": os.path.join(REF_DIR, "ref_01_日常_忙しかった.wav"), "text": "あ、結構忙しかったわね", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_02_日常_お疲れ様.wav"), "text": "今日も一日、お疲れ様", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_03_日常_ありがとう.wav"), "text": "いつも頑張ってくれてありがとう", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_04_日常_起きてて.wav"), "text": "よかったちゃんと起きててくれた", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_05_日常_早起き.wav"), "text": "お店のために早起きしてくれて助かってる", "lang": "日文"},
    ],
    "tsundere": [
        {"path": os.path.join(REF_DIR, "ref_06_傲娇_変なこと.wav"), "text": "言っとくけど変なことはしないからね", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_07_傲娇_キモい.wav"), "text": "割とキモい。普通にキモいから", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_08_傲娇_ここでは.wav"), "text": "あと何度も言うけどここではしない", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_09_傲娇_おやすみ.wav"), "text": "おやすみなさい", "lang": "日文"},
    ],
    "romantic": [
        {"path": os.path.join(REF_DIR, "ref_10_深情_好きって.wav"), "text": "それに、君のこと好きってこと", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_11_深情_大好き.wav"), "text": "好き、大好き", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_12_深情_情けない顔.wav"), "text": "その情けない顔と声…好き", "lang": "日文"},
    ],
    "long": [
        {"path": os.path.join(REF_DIR, "ref_13_长句_表情筋.wav"), "text": "普段使わない表情筋を酷使してるから", "lang": "日文"},
        {"path": os.path.join(REF_DIR, "ref_14_长句_彼女っていう.wav"), "text": "あのさこれは彼女っていうより", "lang": "日文"},
    ],
}

# 反向查找：文件名 → {path, text, lang}
REF_INDEX = {}
for mood, items in REF_WAVES.items():
    for item in items:
        basename = os.path.basename(item["path"])
        REF_INDEX[basename] = item

# 默认参考
default_ref = os.path.join(
    WEBUI_DIR,
    r"logs\xxx\5-wav32k\DLsite Play_4.mp3.reformatted_vocals.flac_0031993280_0032002560.wav"
)

# 文本到情绪模式的映射规则
TEXT_MOODS = {
    "casual": [
        "おはよう", "お疲れ", "ありがとう", "がんば", "大変", "仕事",
        "今日", "また", "さあ", "さて", "もう", "ちゃんと", "しっかり",
    ],
    "tsundere": [
        "キモ", "変態", "変な", "いいわ", "しない", "大丈夫", "おやすみ",
        "だって", "しょうがない", "バカ", "うるさい", "ふん", "哼", "笨蛋",
        "哼", "随便你", "我才没有", "别以为", "哼", "ふん",
    ],
    "romantic": [
        "好き", "大好き", "愛", "君のこと", "あなた", "幸せ", "エッチ",
        "気持ちいい", "大好き", "愛してる", "大好きよ", "宝贝", "老公",
        "喜欢你", "我爱你", "想你", "爱你", "永远",
    ],
}


def pick_ref(text, mood_hint):
    """根据文本内容和情绪提示选择参考音频（返回完整字典）"""
    # 1. 如果显式指定了情绪模式，按模式选
    if mood_hint and mood_hint in REF_WAVES:
        refs = REF_WAVES[mood_hint]
        print(f"DEBUG: mood_hint={mood_hint}, refs count={len(refs)}", file=sys.stderr)
    else:
        # 2. 根据文本关键词匹配情绪
        text_lower = text.lower()
        scores = {}
        for mood, keywords in TEXT_MOODS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[mood] = score
        
        # 3. 有匹配就选最高分的，否则随机
        max_score = max(scores.values())
        if max_score > 0:
            candidates = [m for m, s in scores.items() if s == max_score]
            mood = random.choice(candidates)
            refs = REF_WAVES[mood]
        else:
            # 默认：日常或长句（稳定）
            all_refs = []
            for group in REF_WAVES.values():
                all_refs.extend(group)
            return random.choice(all_refs)
    
    # 4. 在选中的情绪组里随机选一个，增加音色变化
    return random.choice(refs)


def lookup_ref_info(ref_path):
    """查找参考音频的信息（文本和语言）"""
    basename = os.path.basename(ref_path)
    info = REF_INDEX.get(basename)
    if info:
        return info["text"], info["lang"]
    # 找不到就返回空
    return "", "日文"


# ========== 主流程 ==========
text = sys.argv[1]
lang = sys.argv[2] if len(sys.argv) > 2 else "ja"  # 默认日文，夏目的训练集是日文拟合效果最好
mood_hint = sys.argv[3] if len(sys.argv) > 3 else None
ref_wav = sys.argv[4] if len(sys.argv) > 4 else None

# 自动选择参考音频
if ref_wav is None:
    ref_wav = pick_ref(text, mood_hint)

# ref_wav 现在是字典 {path, text, lang}
if isinstance(ref_wav, dict):
    ref_path = ref_wav["path"]
    ref_prompt_text = ref_wav["text"]
    ref_prompt_lang = ref_wav["lang"]
else:
    ref_path = ref_wav
    ref_prompt_text, ref_prompt_lang = lookup_ref_info(ref_wav)

# 打印选择的参考音频
print(f"Selected ref: {os.path.basename(ref_path)}", file=sys.stderr)
print(f"Prompt text: {ref_prompt_text}", file=sys.stderr)
print(f"Prompt lang: {ref_prompt_lang}", file=sys.stderr)

# 获取锁（防止并发/超时重试导致跑两次）
lock_pid, lock_exe = acquire_lock()
if lock_pid is None:
    print("[ERROR] 已有 tts 实例在运行，跳过本次调用", file=sys.stderr)
    sys.exit(0)

try:
    # 硬超时保护
    with TimeoutGuard(HARD_TIMEOUT):
        # 停 llama-server 腾显存
        stop_llama()

        from GPT_SoVITS.inference_webui import get_tts_wav, dict_language

        lang_map = {"zh": "中文", "ja": "日文", "en": "英文", "yue": "粤语", "ko": "韩文"}
        prompt_lang = lang_map.get(lang, lang)
        text_lang = lang_map.get(lang, lang)

        gen = get_tts_wav(
            ref_wav_path=ref_path,
            prompt_text=ref_prompt_text,
            prompt_language=ref_prompt_lang,
            text=text,
            text_language=text_lang,
            how_to_cut="不切",
            top_k=5,
            top_p=0.9,
            temperature=0.7,
            ref_free=True,  # 恢复ref_free=True，只使用音色
            speed=1,
            if_freeze=False,
            inp_refs=None,
            sample_steps=32,
            if_sr=False,
            pause_second=0.3,
        )

        output_wav_path = None
        for item in gen:
            if isinstance(item, tuple) and len(item) == 2:
                sr, audio = item
                
                # 归一化音频到正常音量
                original_max = np.max(np.abs(audio))
                if original_max > 0 and original_max < 10000:  # 如果音量太低
                    gain = 25000.0 / original_max  # 增益到最大幅值约25000
                    audio_float = audio.astype(np.float32) * gain
                    # 防止溢出
                    audio_float = np.clip(audio_float, -32768, 32767).astype(np.int16)
                    audio = audio_float
                    print(f"Applied gain: {gain:.2f}x (original max: {original_max})", file=sys.stderr)
                
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                tag = slugify(text)
                filename = f"tts_{tag}_{random.randint(10000,99999)}.wav"
                out_path = os.path.join(OUTPUT_DIR, filename)
                scipy.io.wavfile.write(out_path, sr, audio)
                output_wav_path = out_path

        # 重启 llama-server，等它完全就绪再输出结果
        if output_wav_path:
            sys.stderr.flush()
            start_llama()
            print(f"[LLAMA] 已就绪，继续输出结果", file=sys.stderr, flush=True)

        # 标准输出返回路径（现在 llama 已经在线，主 session 能处理 announce）
        if output_wav_path:
            sys.stdout.write(output_wav_path + '\n')
            sys.stdout.flush()
        else:
            print("[ERROR] TTS 未生成 wav 文件", file=sys.stderr)
            sys.exit(1)

except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    # 异常退出也要保证 llama 被重启
    try:
        if not _port_open("127.0.0.1", LLAMA_PORT, timeout=0.5):
            subprocess.Popen(
                ["powershell", "-Command", f"Start-Process -WindowStyle Hidden -FilePath '{RESTART_SCRIPT}'"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    except Exception:
        pass
    sys.exit(1)
finally:
    release_lock()

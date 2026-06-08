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
import re
import numpy as np
import scipy.io.wavfile

# --- shared 生命周期模块 ---
_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from skills.shared.llama_lifecycle import (
    acquire_lock, release_lock,
    stop_llama, start_llama,
    TimeoutGuard, register_cleanup_handlers,
)

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
HARD_TIMEOUT = 420  # 秒，超过这个时间强制退出（推理最长5min + llama重启等待最长2min，留余量）


def slugify(text, max_len=20):
    """从文本提取安全文件名标签（保留中英文/数字）"""
    cleaned = re.sub(r'[^\w\u4e00-\u9fff ]', ' ', text, flags=re.ASCII)
    cleaned = re.sub(r'\s+', '_', cleaned).strip('_')
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip('_')
    return cleaned or 'untitled'


# ========== 参考音频目录 ==========
REF_DIR = os.path.join(
    r"C:\Users\TK\.openclaw\workspace\qqbot\skills\tts",
    r"ref_wavs"
)

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
    if mood_hint and mood_hint in REF_WAVES:
        refs = REF_WAVES[mood_hint]
        print(f"DEBUG: mood_hint={mood_hint}, refs count={len(refs)}", file=sys.stderr)
    else:
        text_lower = text.lower()
        scores = {}
        for mood, keywords in TEXT_MOODS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[mood] = score

        max_score = max(scores.values())
        if max_score > 0:
            candidates = [m for m, s in scores.items() if s == max_score]
            mood = random.choice(candidates)
            refs = REF_WAVES[mood]
        else:
            all_refs = []
            for group in REF_WAVES.values():
                all_refs.extend(group)
            return random.choice(all_refs)

    return random.choice(refs)


def lookup_ref_info(ref_path):
    """查找参考音频的信息（文本和语言）"""
    basename = os.path.basename(ref_path)
    info = REF_INDEX.get(basename)
    if info:
        return info["text"], info["lang"]
    return "", "日文"


# ========== 主流程 ==========
text = sys.argv[1]
lang = sys.argv[2] if len(sys.argv) > 2 else "ja"
mood_hint = sys.argv[3] if len(sys.argv) > 3 else None
ref_wav = sys.argv[4] if len(sys.argv) > 4 else None

# 自动选择参考音频
if ref_wav is None:
    ref_wav = pick_ref(text, mood_hint)

if isinstance(ref_wav, dict):
    ref_path = ref_wav["path"]
    ref_prompt_text = ref_wav["text"]
    ref_prompt_lang = ref_wav["lang"]
else:
    ref_path = ref_wav
    ref_prompt_text, ref_prompt_lang = lookup_ref_info(ref_wav)

print(f"Selected ref: {os.path.basename(ref_path)}", file=sys.stderr)
print(f"Prompt text: {ref_prompt_text}", file=sys.stderr)
print(f"Prompt lang: {ref_prompt_lang}", file=sys.stderr)

# 获取锁（使用 shared 模块）
lock_pid, lock_exe = acquire_lock(LOCK_FILE, label="tts")
if lock_pid is None:
    print("[ERROR] 已有 tts 实例在运行，跳过本次调用", file=sys.stderr)
    sys.exit(0)

# 注册清理钩子（使用 shared 模块）
register_cleanup_handlers(
    lock_file=LOCK_FILE,
    llama_port=LLAMA_PORT,
    restart_script=RESTART_SCRIPT,
)

try:
    with TimeoutGuard(HARD_TIMEOUT, lock_file=LOCK_FILE):
        # 停 llama-server 腾显存（使用 shared 模块，含 VRAM 稳定检测）
        stop_llama(port=LLAMA_PORT, wait_vram_stable=True)

        from GPT_SoVITS.inference_webui import get_tts_wav

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
            ref_free=True,
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
                if original_max > 0 and original_max < 10000:
                    gain = 25000.0 / original_max
                    audio_float = audio.astype(np.float32) * gain
                    audio_float = np.clip(audio_float, -32768, 32767).astype(np.int16)
                    audio = audio_float
                    print(f"Applied gain: {gain:.2f}x (original max: {original_max})",
                          file=sys.stderr)

                os.makedirs(OUTPUT_DIR, exist_ok=True)
                tag = slugify(text)
                filename = f"tts_{tag}_{random.randint(10000, 99999)}.wav"
                out_path = os.path.join(OUTPUT_DIR, filename)
                scipy.io.wavfile.write(out_path, sr, audio)
                output_wav_path = out_path

        # 重启 llama-server，等它完全就绪再输出结果
        if output_wav_path:
            sys.stderr.flush()
            start_llama(
                port=LLAMA_PORT,
                exe_path=LLAMA_EXE_PATH,
                model_path=LLAMA_MODEL_PATH,
                log_dir=LLAMA_LOG_DIR,
            )
            print(f"[LLAMA] 已就绪，继续输出结果", file=sys.stderr, flush=True)

        if output_wav_path:
            sys.stdout.write(output_wav_path + '\n')
            sys.stdout.flush()
        else:
            print("[ERROR] TTS 未生成 wav 文件", file=sys.stderr)
            sys.exit(1)

except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
finally:
    release_lock(LOCK_FILE)

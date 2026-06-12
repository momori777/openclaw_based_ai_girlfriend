#!/usr/bin/env python3
"""
GPT-SoVITS TTS 调用脚本 — 子进程自动化流程
用法: python tts_call.py "目标文本" "语言代码" [情绪模式]
语言代码: zh=中文, ja=日文, en=英文
情绪模式: casual=日常温柔, tsundere=傲娇强势, romantic=深情, long=长句稳定, random=随机
输出: 标准输出打印生成的 wav 文件路径

路径: 从 workspace 根目录的 config.yaml 读取

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

# --- 从 workspace/config.yaml 读取路径 ---
_def = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _load_config():
    config_path = os.path.join(_def, 'config.yaml')
    if not os.path.exists(config_path):
        print(f"[ERROR] 找不到 config.yaml: {config_path}", file=sys.stderr)
        print("请先运行 quick_setup.ps1 或在 workspace 根目录创建 config.yaml",
              file=sys.stderr)
        sys.exit(1)
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

_cfg = _load_config()

# --- shared 生命周期模块 ---
if _def not in sys.path:
    sys.path.insert(0, _def)

from skills.shared.llama_lifecycle import (
    acquire_lock, release_lock,
    stop_llama, start_llama,
    TimeoutGuard, register_cleanup_handlers,
)

# Change to WebUI directory
WEBUI_DIR = _cfg['sovits_root']
os.chdir(WEBUI_DIR)
sys.path.insert(0, WEBUI_DIR)

# ========== 路径配置（从 config.yaml 读取） ==========
OUTPUT_DIR = _cfg['tts_temp_output_dir']
LOCK_FILE = os.path.join(OUTPUT_DIR, ".tts_running.lock")

# ========== Llama Server 配置 ==========
LLAMA_LOG_DIR = _cfg['llama_log_dir']
LLAMA_EXE_PATH = _cfg['llama_exe']
LLAMA_MODEL_PATH = _cfg['llama_model']
RESTART_SCRIPT = _cfg['restart_script']
LLAMA_PORT = _cfg.get('llama_port', 8080)

# ========== 硬超时（防止子进程卡死不退出，导致 gateway session 锁死） ==========
HARD_TIMEOUT = 480  # TTS推理~10s + llama重启等待(含重试)最多420s，留余量


def slugify(text, max_len=20):
    """从文本提取安全文件名标签（保留中英文/数字）"""
    cleaned = re.sub(r'[^\w\u4e00-\u9fff ]', ' ', text, flags=re.ASCII)
    cleaned = re.sub(r'\s+', '_', cleaned).strip('_')
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip('_')
    return cleaned or 'untitled'


# ========== 参考音频目录（相对于 tts skill，按角色自动切换） ==========
_tts_dir = os.path.dirname(os.path.abspath(__file__))


def _detect_character():
    """检测当前活跃角色名（从 workspace 的 SOUL.md）"""
    # workspace 路径: skills/tts/tts_call.py -> workspace root
    ws_root = os.path.join(_tts_dir, "..", "..")
    soul_path = os.path.join(ws_root, "SOUL.md")
    if os.path.exists(soul_path):
        with open(soul_path, "r", encoding="utf-8") as f:
            first = f.readline().strip()
        m = re.match(r"^# SOUL\.md\s*-\s*(.+)$", first)
        if m:
            return m.group(1).strip().lower().replace(" ", "-")
    return None


def _resolve_ref_dir():
    """根据活跃角色解析参考音频目录。
    规则: ref_wavs_<角色名> 优先，否则用 ref_wavs（默认夏目）。
    """
    chara = _detect_character()
    if chara:
        chara_dir = os.path.join(_tts_dir, f"ref_wavs_{chara}")
        if os.path.isdir(chara_dir) and os.listdir(chara_dir):
            return chara_dir
    return os.path.join(_tts_dir, "ref_wavs")


REF_DIR = _resolve_ref_dir()


def _load_ref_waves(ref_dir):
    """扫描参考音频目录，按文件名约定归类。
    文件名格式: ref_NN_情绪_文本描述.wav
    情绪 → mood 映射:
      日常/casual → casual
      傲娇/tsundere/困惑 → tsundere
      深情/romantic → romantic
      长句/long → long
    参考文本从文件名提取（去掉前缀和扩展名）或从同目录对应的.txt文件读取。
    """
    MOOD_MAP = {
        "日常": "casual", "casual": "casual",
        "傲娇": "tsundere", "tsundere": "tsundere", "困惑": "tsundere",
        "深情": "romantic", "romantic": "romantic",
        "长句": "long", "long": "long",
    }
    ref_waves = {"casual": [], "tsundere": [], "romantic": [], "long": []}
    if not os.path.isdir(ref_dir):
        return ref_waves
    for fname in sorted(os.listdir(ref_dir)):
        if not fname.lower().endswith(".wav"):
            continue
        fpath = os.path.join(ref_dir, fname)
        stem = os.path.splitext(fname)[0]  # ref_01_日常_おはよう
        parts = stem.split("_")
        # 查找情绪关键词
        mood = None
        for p in parts:
            if p in MOOD_MAP:
                mood = MOOD_MAP[p]
                break
        if mood is None:
            mood = "casual"  # fallback
        # 参考文本：同目录下同名 .txt 文件，否则用文件名剩余部分
        txt_path = os.path.join(ref_dir, stem + ".txt")
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                ref_text = f.read().strip()
        else:
            # 从文件名提取: ref_01_日常_おはよう → おはよう
            # 格式: ref_NN_情绪_文本
            text_parts = []
            capture = False
            for p in parts:
                if capture:
                    text_parts.append(p)
                elif p in MOOD_MAP:
                    capture = True
            ref_text = " ".join(text_parts) if text_parts else stem
        ref_waves[mood].append({
            "path": fpath,
            "text": ref_text,
            "lang": "日文",
        })
    return ref_waves


REF_WAVES = _load_ref_waves(REF_DIR)

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
            ok = start_llama(
                port=LLAMA_PORT,
                exe_path=LLAMA_EXE_PATH,
                model_path=LLAMA_MODEL_PATH,
                log_dir=LLAMA_LOG_DIR,
            )
            if not ok:
                print(f"[LLAMA] 启动失败(VRAM不足或超时)，语音已生成",
                      file=sys.stderr, flush=True)
            else:
                print(f"[LLAMA] 已就绪，继续输出结果", file=sys.stderr, flush=True)

        if output_wav_path:
            sys.stdout.write(output_wav_path + '\n')
            sys.stdout.flush()
        else:
            print("[ERROR] TTS 未生成 wav 文件", file=sys.stderr)
            sys.exit(1)

except TimeoutError:
        # 超时时 wav 可能已生成（start_llama 阶段超时），不要 exit 1
        if output_wav_path and os.path.exists(output_wav_path):
            print(f"[TIMEOUT] 超时但音频已生成: {output_wav_path}", file=sys.stderr, flush=True)
            sys.stdout.write(output_wav_path + '\n')
            sys.stdout.flush()
            sys.exit(0)
        print("[TIMEOUT] 超时，无输出文件", file=sys.stderr, flush=True)
        sys.exit(1)
except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
finally:
    release_lock(LOCK_FILE)

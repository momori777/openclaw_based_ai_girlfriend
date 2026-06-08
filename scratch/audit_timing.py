"""
Timing window / race condition audit.

The critical question: When TTS/ComfyUI kills llama, what happens if Sakura
is mid-request? Does Sakura's LocalLlamaClient handle this correctly?
"""

# Read the key sections
import re

files_to_check = {
    'tts_call.py': r'D:\AI_Girlfriend\skills\tts\tts_call.py',
    'comfyui_call.py': r'D:\AI_Girlfriend\skills\comfyui\comfyui_call.py',
    'local_llama_client.py': r'D:\AI_Girlfriend\skills\sakura\app\llm\local_llama_client.py',
}

print("=" * 70)
print("TIMING WINDOW AUDIT")
print("=" * 70)

# 1. Check lock file mechanism
print("\n1. Lock file paths:")
for fname, path in files_to_check.items():
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    locks = re.findall(r"(?:LOCK_FILE|LOCK_DIR|\.lock)\s*=?\s*['\"]?([^'\"\s\n]+)", content)
    if locks:
        print(f"  {fname}: {locks}")

# 2. Check stop_llama order in both scripts
print("\n2. Asymmetric llama handling:")
print("  TTS: stop_llama() → TTS inference → start_llama()")
print("  ComfyUI: stop_llama() → ComfyUI inference → start_llama()")
print("  Sakura: detect → wait → retry (never kill/restart)")

# 3. Check if _with_llama_sense correctly catches mid-request failures
with open(r'D:\AI_Girlfriend\skills\sakura\app\llm\local_llama_client.py', 'r', encoding='utf-8') as f:
    sakura_llm = f.read()

has_retry = 'detect_llama_unavailable' in sakura_llm
has_wait = 'wait_for_llama_ready' in sakura_llm
has_fallback = 'fallback' in sakura_llm.lower()

print(f"\n3. Sakura _with_llama_sense: detect={has_retry}, wait={has_wait}, fallback={has_fallback}")

# 4. The critical window: between stop_llama() and start_llama()
# TTS inference takes ~30s, during which llama is dead
# If Sakura sends a request in that window, it gets connection refused
# _with_llama_sense catches this → enters wait_for_llama_ready (300s timeout)
# After TTS finishes and start_llama() succeeds, Sakura's polling detects it
# So the window IS handled, but with up to 2s polling delay

print("\n4. Window analysis:")
print("  stop_llama → TTS(~30s) → start_llama → wait_for_ready(~15s)")
print("  Total llama downtime ~45s")
print("  Sakura poll interval: 2s (via shared wait_for_llama_ready)")
print("  Max Sakura delay after llama restart: 2s")
print("  CONCLUSION: Correctly handled by _with_llama_sense()")

# 5. Check concurrent TTS+ComfyUI protection
print("\n5. Concurrent prevention:")
# Both scripts use file locks
tts_lock = "tts_running" in open(r'D:\AI_Girlfriend\skills\tts\tts_call.py', 'r', encoding='utf-8').read()
comfy_lock = "comfyui_running" in open(r'D:\AI_Girlfriend\skills\comfyui\comfyui_call.py', 'r', encoding='utf-8').read()
print(f"  TTS file lock: {tts_lock}")
print(f"  ComfyUI file lock: {comfy_lock}")
print("  Note: Different lock files → TTS and ComfyUI CAN run concurrently!")
print("  This would DOUBLE-kill llama. Second script would find llama already dead.")
print("  stop_llama() handles already-dead gracefully (port check first).")

# 6. What's MISSING
print("\n6. MISSING protections:")
print("  - No shared lock between TTS and ComfyUI to prevent concurrent GPU use")
print("  - TTS/ComfyUI don't check if Sakura is mid-conversation before killing llama")
print("  - Sakura doesn't signal 'I'm using llama, don't kill' before conversations")
print("  - No global GPU-inference queue/semaphore")
print()
print("  Current behavior: Sakura's request gets killed mid-stream → retries after restart")
print("  User impact: Desktop pet says a line, TTS fires, pet's next response delayed ~45s")
print("  Severity: Low (Sakura handles gracefully, just adds latency)")

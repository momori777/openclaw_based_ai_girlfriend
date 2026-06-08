"""Audit: find duplicated code patterns across skills"""
import os, re
from collections import defaultdict

# Check patterns that appear in multiple files
patterns = {
    'stop_llama': r'def stop_llama',
    'start_llama': r'def start_llama',
    'LLAMA_PORT': r'LLAMA_PORT\s*=\s*8080',
    'LLAMA_EXE_PATH': r'LLAMA_EXE_PATH\s*=',
    'LLAMA_MODEL_PATH': r'LLAMA_MODEL_PATH\s*=',
    'taskkill': r'taskkill\s+/f\s+/im\s+llama-server',
    'COMFYUI_ROOT': r'COMFYUI_ROOT\s*=',
    'GPT_SoVITS_root': r'GPT_SoVITS_root\s*=',
    'OUTPUT_DIR': r'OUTPUT_DIR\s*=',
    'file_lock': r'\.lock',
    'restart-llama': r'restart-llama\.ps1',
    'TTS_RUNNING': r'\.tts_running',
    'COMFYUI_RUNNING': r'\.comfyui_running',
}

skills_dir = r'D:\AI_Girlfriend\skills'
results = defaultdict(list)

for root, dirs, files in os.walk(skills_dir):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', 'node_modules', 'third_party', '.git')]
    for f in files:
        if not f.endswith(('.py', '.ps1')):
            continue
        path = os.path.join(root, f)
        rel = os.path.relpath(path, r'D:\AI_Girlfriend')
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
                for name, pattern in patterns.items():
                    if re.search(pattern, content):
                        results[name].append(rel)
        except:
            pass

print("=== Pattern Duplication Report ===\n")
for name, files in sorted(results.items()):
    if len(files) <= 1:
        continue
    print(f"[{name}] appears in {len(files)} files:")
    for f in files:
        print(f"  {f}")
    print()

# Also check if tts_call.py and comfyui_call.py have near-identical structure
print("=== Structural Similarity ===\n")
for pair in [('tts_call.py', 'comfyui_call.py')]:
    print(f"Comparing {pair[0]} vs {pair[1]}...")
    
print("Done")

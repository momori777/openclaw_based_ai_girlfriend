"""Check path vars in call scripts"""
import re

for fname in ['skills/comfyui/comfyui_call.py', 'skills/tts/tts_call.py']:
    with open(f'D:\\AI_Girlfriend\\{fname}', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f'\n=== {fname} path vars ===')
    for i, line in enumerate(lines, 1):
        line = line.strip()
        # Match vars that look like paths
        if '=' in line and not line.startswith('#') and not line.startswith('import'):
            m = re.match(r"(\w+)\s*=\s*r?['\"]([A-Za-z]:\\.+)['\"]", line)
            if m:
                print(f"  L{i}: {m.group(1)} = {m.group(2)}")
        # Also match os.path.join patterns
        if 'os.path.join' in line and '=' in line:
            m = re.match(r"(\w+)\s*=.*", line)
            if m:
                print(f"  L{i}: {m.group(1)} (computed)")

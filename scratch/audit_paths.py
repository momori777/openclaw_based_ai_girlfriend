import os, re, sys
from collections import defaultdict

excluded_dirs = {'.git', 'scratch', 'node_modules', 'runtime', '__pycache__', 'third_party', 'mem0', 'data'}
extensions = ('.py', '.ps1', '.bat', '.md')

all_hardcoded = []

for root, dirs, files in os.walk(r'D:\AI_Girlfriend'):
    dirs[:] = [d for d in dirs if d not in excluded_dirs]
    for f in files:
        if not f.endswith(extensions):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
                for m in re.finditer(r'[A-Z]:\\[^\s\'\"<>|]+', content):
                    p = m.group()
                    # skip common test patterns
                    if any(skip in p.lower() for skip in ['comfyui', 'openclaw', 'ai_girlfriend']):
                        if 'D:\\AI_Girlfriend' in p or 'E:\\comfyui' in p or 'C:\\Users\\TK' in p:
                            all_hardcoded.append((path, p))
                            continue
                        continue
                    all_hardcoded.append((path, p))
        except:
            pass

by_file = defaultdict(set)
for f, p in all_hardcoded:
    by_file[f].add(p)

print("=== Hardcoded absolute paths ===\n")
for f, paths in sorted(by_file.items()):
    print(f)
    for p in sorted(paths):
        print(f"  {p}")
    print()

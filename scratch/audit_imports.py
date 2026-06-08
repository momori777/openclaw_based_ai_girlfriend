"""Verify shared module import paths"""
import sys, os, re

# Check Sakura local_llama_client.py _skill_dir calculation
sakura_file = r'D:\AI_Girlfriend\skills\sakura\app\llm\local_llama_client.py'

with open(sakura_file, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'_skill_dir\s*=\s*(.+?)(?:\n|$)', content)
expr = m.group(1) if m else "NOT FOUND"
print(f"_skill_dir expression: {expr}")

# Compute what _skill_dir actually resolves to
actual = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sakura_file)))))
print(f"_skill_dir actual value: {actual}")

# With _skill_dir in sys.path, what does 'from skills.shared.llama_utils' resolve to?
test_path = os.path.join(actual, 'skills', 'shared', 'llama_utils.py')
print(f"Resolved import path: {test_path}")
print(f"File exists: {os.path.exists(test_path)}")
print()

# BUG confirmed: _skill_dir = D:\AI_Girlfriend\skills
# But 'from skills.shared.llama_utils' with D:\AI_Girlfriend\skills in sys.path
# means Python looks for D:\AI_Girlfriend\skills\skills\shared\llama_utils.py
# The correct parent dir should be D:\AI_Girlfriend (one level up)
correct_parent = os.path.dirname(actual)
print(f"CORRECT parent for sys.path: {correct_parent}")
test_correct = os.path.join(correct_parent, 'skills', 'shared', 'llama_utils.py')
print(f"Correct resolved path: {test_correct}")
print(f"File exists: {os.path.exists(test_correct)}")
print()
print("VERDICT: BUG — _skill_dir is one level too deep for the import to work!")
print("Fix: needs 5 dirnames instead of 4, or parent after 4")
print()

# Also check tts_call.py
tts_file = r'D:\AI_Girlfriend\skills\tts\tts_call.py'
with open(tts_file, 'r', encoding='utf-8') as f:
    tts_content = f.read()
m = re.search(r'_scripts_dir\s*=\s*(.+?)(?:\n|$)', tts_content)
tts_expr = m.group(1) if m else "NOT FOUND"
print(f"tts_call.py _scripts_dir expression: {tts_expr}")

# _scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# __file__ = D:\AI_Girlfriend\skills\tts\tts_call.py
# 1 dirname: D:\AI_Girlfriend\skills\tts
# 2 dirname: D:\AI_Girlfriend\skills
tts_actual = os.path.dirname(os.path.dirname(os.path.abspath(tts_file)))
print(f"tts_call.py _scripts_dir: {tts_actual}")
tts_test = os.path.join(tts_actual, 'skills', 'shared', 'llama_utils.py')
print(f"Resolved: {tts_test}")
print(f"Exists: {os.path.exists(tts_test)}")
print("SAME BUG in tts_call.py!")

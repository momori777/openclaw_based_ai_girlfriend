import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

for name in ['gh2.json', 'gh3.json', 'gh4.json']:
    path = os.path.join(os.environ['TEMP'], name)
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        print(f"\n=== {name} ===")
        for r in data.get('items', []):
            desc = (r.get('description') or '')[:120]
            stars = r['stargazers_count']
            fork_tag = "[FORK]" if r.get('fork') else ""
            print(f"  {r['full_name']:55s}  STAR={stars:5d}  {fork_tag}  {desc}")
    except Exception as e:
        print(f"ERR {name}: {e}")

import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

path = os.path.join(os.environ['TEMP'], 'gh_search2.json')
with open(path, 'r', encoding='utf-8-sig') as f:
    data = json.load(f)

for r in data.get('items', []):
    name = r['full_name']
    stars = r['stargazers_count']
    desc = (r.get('description') or '')[:100]
    print(f"{name:55s} STAR={stars:5d}  {desc}")

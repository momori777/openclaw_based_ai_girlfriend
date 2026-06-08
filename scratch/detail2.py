import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

for name, fname in [('Momori AI GF', 'gh9.json'), ('NANA', 'gh10.json')]:
    path = os.path.join(os.environ['TEMP'], fname)
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            d = json.load(f)
        print(f"\n{'='*70}")
        print(f"=== {name} ===")
        print(f"  Stars: {d.get('stargazers_count', '?')}  Forks: {d.get('forks_count', '?')}")
        print(f"  Language: {d.get('language', '?')}")
        print(f"  Topics: {d.get('topics', [])}")
        print(f"  Description: {d.get('description', '')[:200]}")
        print(f"  Size: {d.get('size', '?')} KB")
        print(f"  Created: {d.get('created_at', '?')}")
        print(f"  Updated: {d.get('updated_at', '?')}")
        print(f"  License: {(d.get('license') or {}).get('spdx_id', 'None')}")
    except Exception as e:
        print(f"\nERR {name}: {e}")

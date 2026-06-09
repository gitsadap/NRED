import json

with open('scratch/old_api.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

programs = set()
for level, progs in data['results'].items():
    for prog in progs.keys():
        programs.add(prog)

print("Programs in old API:")
for p in sorted(programs):
    print(" -", p)

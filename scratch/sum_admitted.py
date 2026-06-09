import json
with open('scratch/curriculum_2569.json') as f:
    data = json.load(f)
total = sum(d['admitted'].get('2569', 0) for d in data['data'])
print(f"Total Admitted 2569 in curriculum-stats: {total}")

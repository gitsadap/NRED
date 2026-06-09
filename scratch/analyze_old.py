import json

with open('scratch/old_api.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

std_codes = []
for level, programs in data['results'].items():
    for program_name, students in programs.items():
        for student in students:
            std_codes.append(student['std_code'])

std_codes.sort()
print(f"Total students: {len(std_codes)}")
print(f"Min std_code: {std_codes[0]}")
print(f"Max std_code: {std_codes[-1]}")
print("Sample min codes:", std_codes[:10])

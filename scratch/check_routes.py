import sys
import re

with open('app/routers/faculty.py', 'r') as f:
    print("--- faculty.py ---")
    for line in f:
        if '@router.' in line or 'def get_my' in line:
            print(line.strip())

with open('app/routers/auth.py', 'r') as f:
    print("--- auth.py ---")
    for line in f:
        if '@router.' in line or 'def ' in line:
            print(line.strip())

import sys
import os
sys.path.insert(0, os.path.abspath("litellm"))
try:
    import litellm
    print("litellm imported successfully")
except ImportError as e:
    print(f"Failed to import litellm: {e}")

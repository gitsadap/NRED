import re

with open("templates/home.html", "r") as f:
    text = f.read()

# Function to replace newlines inside [[ ]] blocks
def replacer(match):
    expr = match.group(0)
    # Remove newlines and extra spaces
    cleaned = " ".join(expr.split())
    return cleaned

# Find all [[ ... ]] blocks and replace them if they contain newlines
new_text = re.sub(r'\[\[.*?\]\]', replacer, text, flags=re.DOTALL)

with open("templates/home.html", "w") as f:
    f.write(new_text)

print("Replaced successfully!")

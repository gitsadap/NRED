import os
import re

file_path = "templates/home.html"
with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Quick Buttons
quick_buttons = re.compile(r"\{% set colors .*?\{% for btn in quick_buttons %\}(.*?)\{% endfor %\}", re.DOTALL)
def qb_replacer(match):
    block = match.group(1)
    block = re.sub(r"\{% set color.*?%\}", "", block)
    block = block.replace("{{ btn.url }}", "[[ btn.url ]]")
    
    # Target Blank conditionally
    block = re.sub(r"\{% if btn.url.startswith\('http'\) %\}target=\"_blank\" rel=\"noopener noreferrer\" \{%.*?%\}", ":target=\"btn.url.startsWith('http') ? '_blank' : null\"", block)
    
    # Image if
    block = block.replace("{% if btn.image %}", "<template v-if=\"btn.image\">")
    block = block.replace("{{ btn.image }}", "[[ btn.image ]]")
    block = block.replace("{{ btn.title }}", "[[ btn.title ]]")
    return '<template v-for="(btn, index) in pageData.quick_buttons" :key="index">' + block + '</template>'

# Wait, `quick_buttons` doesn't exist in pageData because we didn't add it in `api_home`. 
# We should just let the Python script parse it and we will modify `api.py` later.
html = re.sub(r"\{% set colors = \{.*?\n.*?\} %\}\n\s*\{% for btn in quick_buttons %\}", "{% for btn in quick_buttons %}", html, flags=re.DOTALL)

qb_regex = re.compile(r"\{% for btn in quick_buttons %\}(.*?)\{% endfor %\}", re.DOTALL)
html = qb_regex.sub(qb_replacer, html)


# Stats
stats_regex = re.compile(r"\{% for stat in stats %\}(.*?)\{% endfor %\}", re.DOTALL)
def stats_replacer(match):
    block = match.group(1)
    block = block.replace("{{ stat.number }}", "[[ stat.number ]]")
    block = block.replace("{{ stat.label }}", "[[ stat.label ]]")
    block = block.replace("{{ stat.icon }}", "[[ stat.icon ]]")
    return '<template v-for="(stat, index) in pageData.stats" :key="index">' + block + '</template>'

html = stats_regex.sub(stats_replacer, html)


# Awards (there were some missing blocks inside)
# Wait, look at line 969. It's inside a different section! The previous regex didn't catch it probably because it wasn't the exact loop.
html = re.sub(r"\{% set \w+ = .*? %\}", "", html)

awards2_regex = re.compile(r"\{% for award in awards %\}(.*?)\{% endfor %\}", re.DOTALL)
def awk2(m):
    b = m.group(1)
    b = b.replace("{% if award.image_url %}", "<template v-if=\"award.image_url\">")
    b = b.replace("{% else %}", "</template><template v-else>")
    b = b.replace("{% if award.icon == 'academic-cap' %}", "<template v-if=\"award.icon == 'academic-cap'\">")
    b = b.replace("{% elif award.icon == 'beaker' %}", "</template><template v-else-if=\"award.icon == 'beaker'\">")
    b = b.replace("{% elif award.icon == 'globe' %}", "</template><template v-else-if=\"award.icon == 'globe'\">")
    b = b.replace("{% if award.link_url %}", "<template v-if=\"award.link_url\">")
    b = b.replace("{% endif %}", "</template>")
    b = b.replace("{{ award.title }}", "[[ award.title ]]")
    b = b.replace("{{ award.description }}", "[[ award.description ]]")
    b = b.replace("{{ award.recipient }}", "[[ award.recipient ]]")
    return '<template v-for="(award, index) in pageData.awards" :key="index">' + b + '</template>'

# Wait, `awards` was already replaced by the previous python run. Those lines in grep logs (969++) are from ANOTHER loop maybe?
# Ah, the first run replaced ONLY the FIRST match or something. Let's just remove any remaining jinja syntax by blanket replacements for common things.

# Blanket replacements for generic Jinja logic in Vue:
html = html.replace("{% if item.image_url %}", "<template v-if=\"item.image_url\">")
html = html.replace("{% if item.content %}", "<template v-if=\"item.content\">")
html = html.replace("{{ item.content[:150] }}...", "[[ item.content ? item.content.substring(0, 150) + '...' : '' ]]")
html = html.replace("{% endif %}", "</template>")
html = html.replace("{% else %}", "</template><template v-else>")


with open("templates/home.html", "w", encoding="utf-8") as f:
    f.write(html)

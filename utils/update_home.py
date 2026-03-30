import os
import re

file_path = "templates/home.html"
with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Make a backup
with open(file_path + ".vue.bak", "w", encoding="utf-8") as f:
    f.write(html)

# 1. Page Init
page_init_script = """
{% block scripts %}
<script>
window.initPage = (state, pageData) => {
    state.value.title = "หน้าแรก - Department of NRE";
    
    // Fetch home data
    fetch('/api/v1/home')
    .then(res => res.json())
    .then(data => {
        if(data.status === 'success') {
             pageData.value = data.data;
        }
    });
};
</script>
{% endblock %}
"""
html = html.replace("{% block content %}", "{% block content %}\n" + page_init_script)

# Hero Section
html = re.sub(r"\{% set hero_mode.*%\}", "", html)
html = re.sub(r"\{% set hero_title.*%\}", "", html)
html = re.sub(r"\{% set hero_subtitle.*%\}", "", html)

html = html.replace("{% if hero_banner %}", '<template v-if="pageData.banners && pageData.banners.length > 0">')
html = html.replace("{% set title_parts = hero_banner.title.split(' ') %}", '')

# Replace NRED Display splits (Assuming format "NATURAL RESOURCES ENVIRONMENT DEPARTMENT")
nred_text = """
                <template v-if="pageData.banners[0].title">
                <div v-for="(word, i) in pageData.banners[0].title.split(' ')" :key="i" class="nred-line mb-4 md:mb-6 lg:mb-10" data-aos="fade-up" data-aos-duration="1000">
                    <h2 class="text-4xl sm:text-5xl md:text-7xl lg:text-9xl font-black text-white tracking-tight uppercase scramble-text font-outfit break-words md:break-normal"
                        :style="`text-shadow: 0 0 40px ${['rgba(16,185,129,0.6)', 'rgba(59,130,246,0.6)', 'rgba(6,182,212,0.6)', 'rgba(139,92,246,0.6)'][i%4]}`">
                        [[ word ]]
                    </h2>
                </div>
                </template>
"""

# We remove the hardcoded NRED parts
# From: <div class="nred-line mb-4 md:mb-6 lg:mb-10" ... all the way to {% endif %} after Department
start_idx = html.find('<!-- Part 1: NATURAL -->')
end_idx = html.find('<!-- Subtitle (Thai Department Name) -->')
if start_idx != -1 and end_idx != -1:
    html = html[:start_idx] + nred_text + html[end_idx:]

# Hero Subtitle
html = html.replace("{{ hero_banner.subtitle.split(' ')[0] if hero_banner.subtitle else\n                        'ภาควิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม' }}", "[[ 'ภาควิชาทรัพยากรธรรมชาติและสิ่งแวดล้อม' ]]")
html = html.replace("{{ hero_banner.subtitle.split(' ', 1)[1] if hero_banner.subtitle and ' ' in hero_banner.subtitle\n                        else 'คณะเกษตรศาสตร์ ทรัพยากรธรรมชาติและสิ่งแวดล้อม มหาวิทยาลัยนเรศวร' }}", "[[ 'คณะเกษตรศาสตร์ ทรัพยากรธรรมชาติและสิ่งแวดล้อม มหาวิทยาลัยนเรศวร' ]]")

html = html.replace("{% endif %}", "</template>")

# Mission Carousel
mission_regex = re.compile(r"\{% for mi in mission_items %\}(.*?)\{% endfor %\}", re.DOTALL)

def mission_replacer(match):
    block = match.group(1)
    # Convert block to Vue
    block = block.replace("{% set icon_colors =", "<!--")
    block = block.replace("} %}", "-->")
    block = block.replace("data-icon=\"{{ mi.icon }}\"", ":data-icon=\"mi.icon\"")
    block = block.replace("data-color=\"{{ mi.color }}\"", ":data-color=\"mi.color\"")
    
    # Just remove static colored conditional and use dynamic
    block = re.sub(r"class=\"mission-card-icon(.*?)bg-gradient-to-br.*?\"", 'class="mission-card-icon w-16 h-16 rounded-full flex items-center justify-center mb-6 text-white shadow-lg bg-gradient-to-br from-green-500/40 to-emerald-600/40"', block)

    # Convert icon if/else to Vue
    # Actually we can just render the icon directly if it's SVG string or we keep the ugly if/else as v-if
    block = block.replace("{% if mi.icon == 'academic-cap' %}", '<template v-if="mi.icon === \'academic-cap\'">')
    block = block.replace("{% elif mi.icon == 'cog' %}", '</template><template v-else-if="mi.icon === \'cog\'">')
    block = block.replace("{% elif mi.icon == 'beaker' %}", '</template><template v-else-if="mi.icon === \'beaker\'">')
    block = block.replace("{% elif mi.icon == 'globe' %}", '</template><template v-else-if="mi.icon === \'globe\'">')
    block = block.replace("{% elif mi.icon == 'heart' %}", '</template><template v-else-if="mi.icon === \'heart\'">')
    block = block.replace("{% elif mi.icon == 'users' %}", '</template><template v-else-if="mi.icon === \'users\'">')
    block = block.replace("{% else %}", '</template><template v-else>')
    block = block.replace("{% endif %}", '</template>')
    
    block = block.replace("{{ mi.title }}", "[[ mi.title ]]")
    block = block.replace("{{ mi.desc }}", "[[ mi.description ]]")
    
    return '<template v-for="(mi, index) in pageData.missions" :key="index">' + block + '</template>'

html = mission_regex.sub(mission_replacer, html)

# Courses
course_regex = re.compile(r"\{% for course in courses %\}(.*?)\{% endfor %\}", re.DOTALL)
def course_replacer(match):
    block = match.group(1)
    block = block.replace("{{ course.youtube_url }}", "[[ course.youtube_url ]]")
    block = block.replace("{{ course.image_url }}", "[[ course.image_url ]]")
    block = block.replace("{{ course.name_th }}", "[[ course.name_th ]]")
    block = block.replace("{{ course.name_en }}", "[[ course.name_en ]]")
    block = block.replace("{{ course.degree }}", "[[ course.degree ]]")
    block = block.replace("href=\"{{ course.url }}\"", ":href=\"course.url\"")
    return '<template v-for="(course, index) in pageData.courses" :key="index">' + block + '</template>'

html = course_regex.sub(course_replacer, html)


# Unified Updates (News & Activity)
unified_regex = re.compile(r"\{% for item in unified_updates %\}(.*?)\{% endfor %\}", re.DOTALL)
def unified_replacer(match):
    block = match.group(1)
    block = block.replace("{{ item.display_type }}", "[[ item.type ]]")
    block = block.replace("{% if item.display_type == 'News' %}", "<template v-if=\"item.type === 'News'\">")
    block = block.replace("{% else %}", "</template><template v-else>")
    block = block.replace("{% endif %}", "</template>")
    block = block.replace("{{ '/news/' ~ item.id }}", "[[ '/news/' + item.id ]]")
    block = block.replace("{{ '/activities/' ~ item.id }}", "[[ '/activities/' + item.id ]]")
    block = block.replace("href=\"{{ '/news/' ~ item.id if item.display_type == 'News' else '/activities/' ~ item.id }}\"", ":href=\"item.type === 'News' ? '/news/' + item.id : '/activities/' + item.id\"")
    block = block.replace("{{ item.image }}", "[[ item.image ]]")
    block = block.replace("{{ item.created_at.strftime('%d %b %Y') if item.created_at else '' }}", "[[ item.created_at ? new Date(item.created_at).toLocaleDateString() : '' ]]")
    block = block.replace("{{ item.title }}", "[[ item.title ]]")
    return '<template v-for="(item, index) in pageData.updates" :key="index">' + block + '</template>'

html = unified_regex.sub(unified_replacer, html)


# Awards
awards_regex = re.compile(r"\{% for award in awards %\}(.*?)\{% endfor %\}", re.DOTALL)
def awards_replacer(match):
    block = match.group(1)
    block = block.replace("{{ award.image_url }}", "[[ award.image_url ]]")
    block = block.replace("{{ award.title }}", "[[ award.title ]]")
    block = block.replace("{{ award.recipient }}", "[[ award.recipient ]]")
    block = block.replace("{{ award.description }}", "[[ award.description ]]")
    return '<template v-for="(award, index) in pageData.awards" :key="index">' + block + '</template>'

html = awards_regex.sub(awards_replacer, html)


# Write back
with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)
print("Updated home.html safely")

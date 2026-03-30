import re

with open("templates/layout.html", "r", encoding="utf-8") as f:
    content = f.read()

# Replace Jinja variables with Vue (assuming we change some manually too)
# Actually, I will just manually edit layout.html using script for exact replaces
replacements = [
    ("{{ title }}", "[[ state.title || 'Department of NRE' ]]"),
    ("{{ description | default('คณะเกษตรศาสตร์ฯ มหาวิทยาลัยนเรศวร') }}", "[[ state.description || 'คณะเกษตรศาสตร์ฯ มหาวิทยาลัยนเรศวร' ]]"),
    ("<img src=\"{{ site_logo }}\"", "<img :src=\"globalContext.site_logo || '/assets/images/logo_new.png'\""),
    ("{{\n                        site_title }}", "[[ globalContext.site_title || 'Loading...' ]]"),
    ("{% for item in menu_items %}", "<template v-for=\"(item, index) in globalContext.menu_items\" :key=\"index\">"),
    ("{% endfor %}", "</template>"),
    ("{% if item.children %}", "<template v-if=\"item.children && item.children.length > 0\">"),
    ("{% endif %}", "</template>"),
    ("href=\"{{ item.url }}\"", ":href=\"item.url\""),
    ("{{ item.label }}", "[[ item.label ]]"),
    ("href=\"{{ child.url }}\"", ":href=\"child.url\""),
    ("{{ child.label }}", "[[ child.label ]]"),
    ("sub-{{ loop.index }}", "sub-[[ index ]]"),
    ("onclick=\"toggleSubmenu('sub-{{ loop.index }}')\"", "@click=\"toggleSubmenu(`sub-${index}`)\""),
    ("{{ contacts.get('address', '99 หมู่ 9 ต.ท่าโพธิ์ อ.เมือง จ.พิษณุโลก 65000') }}", "[[ globalContext.contacts?.address || '99 หมู่ 9 ต.ท่าโพธิ์ อ.เมือง จ.พิษณุโลก 65000' ]]"),
    ("{{ contacts.get('phone', '0-5596-2710') }}", "[[ globalContext.contacts?.phone || '0-5596-2710' ]]"),
    ("{{ contacts.get('email', 'aggie@nu.ac.th') }}", "[[ globalContext.contacts?.email || 'aggie@nu.ac.th' ]]"),
    ("{% if contacts.get('facebook') %}", "<template v-if=\"globalContext.contacts?.facebook\">"),
    ("href=\"{{ contacts.get('facebook') }}\"", ":href=\"globalContext.contacts?.facebook\""),
    ("{% if contacts.get('youtube') %}", "<template v-if=\"globalContext.contacts?.youtube\">"),
    ("href=\"{{ contacts.get('youtube') }}\"", ":href=\"globalContext.contacts?.youtube\""),
    ("{% if contacts.get('line') %}", "<template v-if=\"globalContext.contacts?.line\">"),
    ("href=\"{{ contacts.get('line') }}\"", ":href=\"globalContext.contacts?.line\""),
    ("{{ site_footer }}", "[[ globalContext.site_footer ]]"),
]

for old, new in replacements:
    content = content.replace(old, new)


# Inject Vue CDN and Init
vue_script = """
    <!-- Vue 3 -->
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
"""
content = content.replace("<!-- Tailwind -->", vue_script + "\n    <!-- Tailwind -->")

vue_init = """
    <script>
        const { createApp, ref, onMounted } = Vue;
        
        const app = createApp({
            delimiters: ['[[', ']]'],
            setup() {
                const globalContext = ref({
                    site_title: 'Loading...',
                    site_logo: '',
                    menu_items: [],
                    contacts: {},
                    site_footer: ''
                });
                
                const state = ref({
                    title: 'Department of NRE',
                    description: ''
                });

                // Can add extra reactive refs dynamically by the page
                const pageData = ref({});

                onMounted(async () => {
                    try {
                        const res = await fetch('/api/v1/context');
                        const data = await res.json();
                        if(data.status === 'success') {
                            globalContext.value = data.data;
                        }
                    } catch(e) {
                        console.error("Failed to load global context:", e);
                    }
                    
                    if (window.initPage) {
                        window.initPage(state, pageData);
                    }
                });

                // Toggle Submenu helper inside Vue
                const toggleSubmenu = (id) => {
                    document.getElementById(id).classList.toggle('hidden');
                };

                return { globalContext, state, pageData, toggleSubmenu }
            }
        });
        
        // Wait till DOM is ready to mount
        document.addEventListener('DOMContentLoaded', () => {
            app.mount('body');
        });
    </script>
"""
content = content.replace("{% block scripts %}{% endblock %}", "{% block scripts %}{% endblock %}\n" + vue_init)

with open("templates/layout.html", "w", encoding="utf-8") as f:
    f.write(content)


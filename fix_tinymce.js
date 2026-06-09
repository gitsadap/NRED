function safeSetTinyContent(id, content) {
    if (typeof tinymce !== 'undefined' && tinymce.get(id)) {
        tinymce.get(id).setContent(content || '');
    } else {
        const el = document.getElementById(id);
        if (el) el.value = content || '';
    }
}
function safeGetTinyContent(id) {
    if (typeof tinymce !== 'undefined' && tinymce.get(id)) {
        return tinymce.get(id).getContent();
    } else {
        const el = document.getElementById(id);
        return el ? el.value : '';
    }
}

from __future__ import annotations

from dataclasses import dataclass
from html import escape as html_escape
from typing import Iterable, Optional
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup, Comment  
except Exception:  
    BeautifulSoup = None  
    Comment = None  


@dataclass(frozen=True)
class SanitizerConfig:
    allowed_tags: frozenset[str]
    allowed_iframe_hosts: frozenset[str]
    allow_data_images: bool = True


RICH_HTML_CONFIG = SanitizerConfig(
    allowed_tags=frozenset(
        {
            
            "section",
            "article",
            "header",
            "footer",
            "nav",
            "main",
            "div",
            "span",
            "p",
            "br",
            "hr",
            "strong",
            "b",
            "em",
            "i",
            "u",
            "s",
            "blockquote",
            "pre",
            "code",
            "small",
            "sup",
            "sub",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "ol",
            "li",
            
            "table",
            "thead",
            "tbody",
            "tfoot",
            "tr",
            "th",
            "td",
            "caption",
            
            "img",
            "figure",
            "figcaption",
            "iframe",
            
            "a",
        }
    ),
    allowed_iframe_hosts=frozenset(
        {
            "www.youtube.com",
            "youtube.com",
            "www.youtube-nocookie.com",
            "youtube-nocookie.com",
        }
    ),
)


SVG_ICON_CONFIG = SanitizerConfig(
    allowed_tags=frozenset(
        {
            "svg",
            "g",
            "path",
            "circle",
            "rect",
            "line",
            "polyline",
            "polygon",
            "ellipse",
            "defs",
            "lineargradient",
            "radialgradient",
            "stop",
            "title",
            "desc",
        }
    ),
    allowed_iframe_hosts=frozenset(),
    allow_data_images=False,
)


_DROP_TAGS = {
    "script",
    "style",
    "template",
    "object",
    "embed",
    "applet",
    "meta",
    "link",
    "base",
    "form",
    "input",
    "button",
    "textarea",
    "select",
    "option",
}


def _iter_all_tags(soup) -> Iterable:
    return soup.find_all(True)


def _is_safe_url(url: str, *, allow_data_images: bool, context: str) -> bool:
    if not url:
        return False
    url = str(url).strip()

    
    if url.startswith("#") or url.startswith("/"):
        return True

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()

    if scheme in ("http", "https", "mailto", "tel"):
        return True

    if scheme == "data":
        if not allow_data_images:
            return False
        
        if context != "img_src":
            return False
        return url.lower().startswith("data:image/")

    return False


def _sanitize_tag_attributes(tag, *, cfg: SanitizerConfig) -> None:
    name = (tag.name or "").lower()
    attrs = dict(tag.attrs or {})

    for attr_name in list(attrs.keys()):
        lower_attr = attr_name.lower()

        
        if lower_attr.startswith("on"):
            tag.attrs.pop(attr_name, None)
            continue

        
        if lower_attr in {"srcdoc"}:
            tag.attrs.pop(attr_name, None)
            continue

        
        if lower_attr in {"href", "src"}:
            value = attrs.get(attr_name)
            url_value = value[0] if isinstance(value, list) and value else value
            context = "img_src" if (name == "img" and lower_attr == "src") else "url"
            if not _is_safe_url(str(url_value or ""), allow_data_images=cfg.allow_data_images, context=context):
                tag.attrs.pop(attr_name, None)
                continue

            
            if name == "iframe" and lower_attr == "src":
                parsed = urlparse(str(url_value))
                host = (parsed.hostname or "").lower()
                if not host or host not in cfg.allowed_iframe_hosts:
                    tag.attrs.pop(attr_name, None)
                    continue

        
        allowed_global = {"class", "id", "title", "style"}
        allowed_by_tag = {
            "a": {"href", "title", "target", "rel"},
            "img": {"src", "alt", "title", "width", "height", "loading", "decoding", "referrerpolicy"},
            "iframe": {
                "src",
                "width",
                "height",
                "allow",
                "allowfullscreen",
                "frameborder",
                "loading",
                "referrerpolicy",
            },
            "table": {"border", "cellpadding", "cellspacing"},
            "th": {"colspan", "rowspan", "scope"},
            "td": {"colspan", "rowspan"},
            
            "svg": {"xmlns", "viewbox", "fill", "stroke", "stroke-width", "width", "height", "class", "aria-hidden"},
            "path": {"d", "fill", "stroke", "stroke-width", "fill-rule", "clip-rule"},
            "circle": {"cx", "cy", "r", "fill", "stroke", "stroke-width"},
            "rect": {"x", "y", "width", "height", "rx", "ry", "fill", "stroke", "stroke-width"},
            "line": {"x1", "y1", "x2", "y2", "stroke", "stroke-width"},
            "polyline": {"points", "fill", "stroke", "stroke-width"},
            "polygon": {"points", "fill", "stroke", "stroke-width"},
            "ellipse": {"cx", "cy", "rx", "ry", "fill", "stroke", "stroke-width"},
            "stop": {"offset", "stop-color", "stop-opacity"},
            "lineargradient": {"id", "x1", "y1", "x2", "y2", "gradientunits"},
            "radialgradient": {"id", "cx", "cy", "r", "fx", "fy", "gradientunits"},
        }

        allowed = allowed_global | allowed_by_tag.get(name, set())
        if lower_attr not in {a.lower() for a in allowed}:
            tag.attrs.pop(attr_name, None)

    
    if name == "a":
        target = (tag.attrs.get("target") or "").strip().lower()
        if target == "_blank":
            rel = (tag.attrs.get("rel") or "")
            rel_str = " ".join(rel) if isinstance(rel, list) else str(rel)
            rel_tokens = {t for t in rel_str.split() if t}
            rel_tokens.update({"noopener", "noreferrer"})
            tag.attrs["rel"] = " ".join(sorted(rel_tokens))


def sanitize_html_fragment(html: Optional[str], *, cfg: SanitizerConfig = RICH_HTML_CONFIG) -> str:
    """
    Best-effort sanitizer for HTML fragments stored in DB and rendered with `|safe`.
    - Drops scripts and inline event handlers
    - Restricts iframe src to allowlist hosts
    - Strips dangerous URL schemes (javascript:, etc.)
    """
    if not html:
        return ""

    raw = str(html)

    if BeautifulSoup is None:  
        
        return html_escape(raw)

    soup = BeautifulSoup(raw, "html.parser")

    
    try:
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):  
            comment.extract()
    except Exception:
        pass

    for tag in list(_iter_all_tags(soup)):
        tag_name = (tag.name or "").lower()

        if tag_name in _DROP_TAGS:
            tag.decompose()
            continue

        if tag_name not in cfg.allowed_tags:
            tag.unwrap()
            continue

        _sanitize_tag_attributes(tag, cfg=cfg)

    
    return "".join(str(node) for node in soup.contents)


def sanitize_rich_html(html: Optional[str]) -> str:
    return sanitize_html_fragment(html, cfg=RICH_HTML_CONFIG)


def sanitize_svg_icon(html: Optional[str]) -> str:
    return sanitize_html_fragment(html, cfg=SVG_ICON_CONFIG)

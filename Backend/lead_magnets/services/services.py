"""
services.py — WeasyPrint PDF generation + template rendering
"""

import os
import re
import logging
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def _is_raw_html_key(key: str) -> bool:
    """Keys whose values must be injected as raw HTML without escaping."""
    return (
        key.endswith("_html")
        or key in ("toc_html", "toc_sections_html")
        or key.startswith("customTitle")
        or key.endswith(("_insight", "_tip", "_stat"))
    )


def _safe_escape(value: str) -> str:
    """Minimal HTML escaping for plain-text template values."""
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_IMG_LAYOUT_ATTRS = re.compile(
    r'''\s*(?:style|width|height|align|hspace|vspace)\s*=\s*(?:"[^"]*"|'[^']*'|\S+)''',
    re.IGNORECASE,
)


def _sanitize_section_html(html: str) -> str:
    """
    Sanitize AI-generated section HTML before injection into the template.
    Strips all layout-affecting attributes from <img> tags so the stylesheet
    takes full control of image sizing and positioning.
    """
    if not html or "<img" not in html:
        return html

    def _clean_img(m: re.Match) -> str:
        return _IMG_LAYOUT_ATTRS.sub("", m.group(0))

    html = re.sub(r'<img\b[^>]*>', _clean_img, html, flags=re.IGNORECASE)

    html = re.sub(
        r'(<p)\b([^>]*?)\s+style\s*=\s*(?:"[^"]*"|\'[^\']*\')([^>]*>(\s*<img\b[^>]*>\s*)</p>)',
        r'\1\2\3',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return html


def _resolve_if_blocks(s: str, variables: dict) -> str:
    """
    Stack-based {{#if KEY}}...{{/if}} resolver.
    Handles nested blocks correctly at any depth.
    """
    TOKEN = re.compile(r'\{\{#if\s+(\w+)\}\}|\{\{/if\}\}')

    changed = True
    while changed:
        changed = False
        tokens = list(TOKEN.finditer(s))

        for i, tok in enumerate(tokens):
            if not tok.group(0).startswith('{{#if'):
                continue

            depth = 1
            for j in range(i + 1, len(tokens)):
                if tokens[j].group(0).startswith('{{#if'):
                    depth += 1
                else:
                    depth -= 1
                    if depth == 0:
                        key   = tok.group(1)
                        val   = variables.get(key, "")
                        inner = s[tok.end():tokens[j].start()]
                        keep  = inner if (val and str(val).strip()) else ""
                        s     = s[:tok.start()] + keep + s[tokens[j].end():]
                        changed = True
                        break

            if changed:
                break

    return s


def render_template(template_html: str, variables: dict) -> str:
    """
    Render a Mustache-style HTML template.

    Pass 1 — Resolve all {{#if KEY}}...{{/if}} blocks using a stack-based
              parser. Correctly handles nested blocks at any depth.

    Pass 2 — Substitute {{KEY}} tokens.
              • _html / toc / customTitle keys → raw HTML (no escaping)
              • All other keys                 → HTML-escaped plain text
              • Unknown keys                   → empty string
    """
    result = _resolve_if_blocks(template_html, variables)

    result = re.sub(r'\n[ \t]*\n[ \t]*\n+', '\n\n', result)

    def _replace_token(m: re.Match) -> str:
        key = m.group(1).strip()
        val = variables.get(key)
        if val is None:
            return ""
        val_str = val if isinstance(val, str) else str(val)
        if _is_raw_html_key(key):
            return _sanitize_section_html(val_str)
        return _safe_escape(val_str)

    return re.sub(r"\{\{\s*([\w]+)\s*\}\}", _replace_token, result)


# ─────────────────────────────────────────────────────────────────────────────
# WEASYPRINT SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class WeasyPrintService:
    """
    PDF generation service using WeasyPrint (free, open source).
    """

    TEMPLATES_DIR = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),  # services/
        "..",                                         # lead_magnets/
        "templates"                                   # lead_magnets/templates/
    ))

    TEMPLATE_REGISTRY = {
        "modern-guide": "Template.html",
    }

    def __init__(self):
        logger.info("WeasyPrintService initialised | TEMPLATES_DIR=%s", self.TEMPLATES_DIR)

    def _get_template_path(self, template_id: str) -> str:
        filename = self.TEMPLATE_REGISTRY.get(template_id, f"{template_id}.html")
        return os.path.join(self.TEMPLATES_DIR, filename)

    def list_templates(self) -> list:
        templates = []
        for tid, fname in self.TEMPLATE_REGISTRY.items():
            fpath = os.path.join(self.TEMPLATES_DIR, fname)
            templates.append({
                "id":          tid,
                "name":        tid.replace("-", " ").title(),
                "file_exists": os.path.exists(fpath),
            })
        return templates

    def preview_template(self, template_id: str, variables: dict) -> str:
        path = self._get_template_path(template_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Template not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        return render_template(html, variables)

    def generate_pdf(self, template_id: str, variables: dict) -> dict:
        # ── 1. Load template ──────────────────────────────────────────────
        path = self._get_template_path(template_id)

        logger.info(
            "WeasyPrint | template=%s | path=%s | exists=%s",
            template_id, path, os.path.exists(path)
        )

        if not os.path.exists(path):
            return {
                "success": False,
                "error":   f"Template file not found: {path}",
                "details": f"TEMPLATES_DIR={self.TEMPLATES_DIR}",
            }

        with open(path, "r", encoding="utf-8") as f:
            template_html = f.read()

        logger.info(
            "WeasyPrint | template loaded | size=%s chars | preview=%s",
            f"{len(template_html):,}",
            template_html[:100].replace("\n", " ")
        )

        # ── 2. Render variables into HTML ─────────────────────────────────
        rendered_html = render_template(template_html, variables)

        # Diagnostics
        remaining_ifs    = rendered_html.count("{{#if")
        remaining_endifs = rendered_html.count("{{/if}}")
        escaped_tags     = rendered_html.count("&lt;p&gt;") + rendered_html.count("&lt;h3&gt;")

        if remaining_ifs or remaining_endifs:
            logger.error(
                "render_template left %d unresolved {{#if}} and %d {{/if}}",
                remaining_ifs, remaining_endifs,
            )
        if escaped_tags > 5:
            logger.error(
                "%d escaped HTML tags detected — section HTML vars not injected as raw HTML",
                escaped_tags,
            )

        # ── 3. Render PDF with WeasyPrint ─────────────────────────────────
        try:
            font_config = FontConfiguration()

            # Base URL set to templates dir so relative assets resolve correctly
            pdf_data = HTML(
                string=rendered_html,
                base_url=self.TEMPLATES_DIR,
            ).write_pdf(font_config=font_config)

            title    = variables.get("documentTitle") or variables.get("mainTitle") or "document"
            filename = re.sub(r"[^\w\-]", "-", str(title).lower())[:60] + ".pdf"

            logger.info(
                "WeasyPrint success | %s bytes | %s",
                f"{len(pdf_data):,}", filename,
            )

            return {
                "success":      True,
                "pdf_data":     pdf_data,
                "filename":     filename,
                "content_type": "application/pdf",
            }

        except Exception as e:
            logger.error("WeasyPrint error: %s", e)
            return {
                "success": False,
                "error":   "WeasyPrint PDF generation failed",
                "details": str(e),
            }
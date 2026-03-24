"""
services.py — DocRaptor PDF generation + template rendering
"""

import os
import re
import logging
import requests
from django.conf import settings

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


def _resolve_if_blocks(s: str, variables: dict) -> str:
    """
    Stack-based {{#if KEY}}...{{/if}} resolver.

    Handles nested blocks correctly at any depth.
    The previous regex approach consumed the FIRST {{/if}} it found —
    the inner one in a nested block — leaving orphan {{/if}} tokens that
    PrinceXML rendered as visible text on blank pages.
    """
    TOKEN = re.compile(r'\{\{#if\s+(\w+)\}\}|\{\{/if\}\}')

    changed = True
    while changed:
        changed = False
        tokens = list(TOKEN.finditer(s))

        for i, tok in enumerate(tokens):
            if not tok.group(0).startswith('{{#if'):
                continue

            # Find the matching {{/if}} at depth 0
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
                break  # restart scan on modified string

    return s


def render_template(template_html: str, variables: dict) -> str:
    """
    Render a Mustache-style HTML template.

    Pass 1 — Resolve ALL {{#if KEY}}...{{/if}} blocks using a stack-based
              parser. Correctly handles nested blocks at any depth.
              Falsy blocks are removed entirely — no orphan tags, no blank pages.

    Pass 2 — Substitute {{KEY}} tokens.
              • _html / toc / customTitle keys → raw HTML (no escaping)
              • All other keys                 → HTML-escaped plain text
              • Unknown keys                   → empty string
    """
    result = _resolve_if_blocks(template_html, variables)

    # Clean up excessive blank lines left after block removal
    result = re.sub(r'\n[ \t]*\n[ \t]*\n+', '\n\n', result)

    def _replace_token(m: re.Match) -> str:
        key = m.group(1).strip()
        val = variables.get(key)
        if val is None:
            return ""
        val_str = val if isinstance(val, str) else str(val)
        return val_str if _is_raw_html_key(key) else _safe_escape(val_str)

    return re.sub(r"\{\{\s*([\w]+)\s*\}\}", _replace_token, result)


# ─────────────────────────────────────────────────────────────────────────────
# DOCRAPTOR SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class DocRaptorService:

    TEMPLATES_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
    )

    TEMPLATE_REGISTRY = {
        "modern-guide": "Template.html",
        "brand-assets":  "BrandAssets.html",
    }

    def __init__(self):
        self.api_key   = os.getenv("DOCRAPTOR_API_KEY", "")
        self.test_mode = os.getenv("DOCRAPTOR_TEST_MODE", "false").lower() == "true"
        self.api_url   = "https://docraptor.com/docs"

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
        if not os.path.exists(path):
            return {
                "success": False,
                "error":   f"Template file not found: {path}",
                "details": f"Checked: {path}",
            }

        with open(path, "r", encoding="utf-8") as f:
            template_html = f.read()

        # ── DIAGNOSTIC: log template fingerprint so we can confirm the
        #    correct file is being served after each deploy.
        logger.info(
            f"DIAG template | path={path} "
            f"img-slot={'img-slot' in template_html} "
            f"img-block={'img-block' in template_html} "
            f"ph-icon={'ph-icon' in template_html} "
            f"if-image-1={'{' + '{#if image_1_url}' + '}' in template_html} "
            f"size={len(template_html):,}"
        )

        # ── Image URL diagnostic: log which image slots are populated ─────
        for i in range(1, 4):
            url = variables.get(f"image_{i}_url", "")
            logger.info(
                f"DIAG image_{i}_url | present={bool(url)} "
                f"value={url[:60] if url else 'ABSENT'!r}"
            )

        # ── 2. Render ─────────────────────────────────────────────────────
        rendered_html = render_template(template_html, variables)

        # ── DIAGNOSTIC: confirm {{#if}} blocks fully resolved ─────────────
        remaining_ifs    = rendered_html.count("{{#if")
        remaining_endifs = rendered_html.count("{{/if}}")
        escaped_tags     = rendered_html.count("&lt;p&gt;") + rendered_html.count("&lt;h3&gt;")
        real_tags        = rendered_html.count("<p>") + rendered_html.count("<h3>")

        logger.info(
            f"DIAG rendered | "
            f"remaining_if={remaining_ifs} remaining_endif={remaining_endifs} "
            f"real_tags={real_tags} escaped_tags={escaped_tags} "
            f"len={len(rendered_html):,}"
        )

        if remaining_ifs or remaining_endifs:
            logger.error(
                f"render_template left {remaining_ifs} unresolved {{{{#if}}}} "
                f"and {remaining_endifs} {{{{/if}}}} — will print as text/blank pages."
            )
        if escaped_tags > 5:
            logger.error(
                f"{escaped_tags} escaped HTML tags detected — "
                "section_*_html vars were not injected as raw HTML."
            )

        # ── 3. Send to DocRaptor ──────────────────────────────────────────
        if not self.api_key:
            return {
                "success": False,
                "error":   "DOCRAPTOR_API_KEY not configured",
                "details": "Set the DOCRAPTOR_API_KEY environment variable.",
            }

        try:
            payload = {
                "user_credentials": self.api_key,
                "doc": {
                    "document_content": rendered_html,
                    "document_type":    "pdf",
                    "test":             self.test_mode,
                    "prince_options": {
                        "media":   "print",
                        "baseurl": getattr(settings, "SITE_URL", "https://www.kyro.com"),
                    },
                },
            }

            logger.info(
                f"→ DocRaptor | test={self.test_mode} | html={len(rendered_html):,} chars"
            )

            resp = requests.post(
                self.api_url,
                json    = payload,
                headers = {"Content-Type": "application/json"},
                timeout = 120,
            )

            if resp.status_code == 200:
                title    = variables.get("documentTitle") or variables.get("mainTitle") or "document"
                filename = re.sub(r"[^\w\-]", "-", str(title).lower())[:60] + ".pdf"
                logger.info(f"✅ DocRaptor success | {len(resp.content):,} bytes | {filename}")
                return {
                    "success":      True,
                    "pdf_data":     resp.content,
                    "filename":     filename,
                    "content_type": "application/pdf",
                }
            else:
                err = resp.text[:600] if resp.text else "No response body"
                logger.error(f"DocRaptor HTTP {resp.status_code}: {err}")
                return {
                    "success": False,
                    "error":   f"DocRaptor returned HTTP {resp.status_code}",
                    "details": err,
                }

        except requests.Timeout:
            return {
                "success": False,
                "error":   "DocRaptor request timed out after 120s",
                "details": "Try reducing content size or contact DocRaptor support.",
            }
        except Exception as e:
            logger.error(f"DocRaptor exception: {e}")
            return {
                "success": False,
                "error":   "Unexpected error calling DocRaptor",
                "details": str(e),
            }
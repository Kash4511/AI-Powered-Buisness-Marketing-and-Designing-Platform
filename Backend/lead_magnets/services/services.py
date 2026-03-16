"""
services.py — DocRaptor PDF generation + template rendering

ROOT CAUSE FIX:
  The previous render_template() was HTML-escaping ALL variables, turning
  section_*_html content like <p>text</p><h3>heading</h3> into literal visible
  text: &lt;p&gt;text&lt;/p&gt;&lt;h3&gt;heading&lt;/h3&gt;

  This fix:
  1. Detects section_*_html keys and injects them as RAW HTML (no escaping).
  2. All other vars are plain-text escaped normally.
  3. {{#if key}}...{{/if}} blocks are resolved FIRST — if image_N_url is empty,
     the entire <img> block is removed, preventing broken/random images.
"""

import os
import re
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE RENDERER — the critical fix
# ─────────────────────────────────────────────────────────────────────────────

def _is_raw_html_key(key: str) -> bool:
    """Keys whose values must be injected as raw HTML without escaping."""
    return (
        key.endswith("_html") or 
        key == "toc_html" or
        key.startswith("customTitle") or 
        key.endswith("_insight") or 
        key.endswith("_tip") or 
        key.endswith("_stat")
    )


def _safe_escape(value: str) -> str:
    """Minimal HTML escaping for plain-text template values."""
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    value = value.replace("&", "&amp;")
    value = value.replace("<", "&lt;")
    value = value.replace(">", "&gt;")
    return value


def render_template(template_html: str, variables: dict) -> str:
    """
    Two-pass Mustache-style renderer.

    Pass 1 — Resolve {{#if key}}...{{/if}} blocks.
              Block content is kept if variables[key] is a non-empty string.
              This removes image tags entirely when no URL is provided,
              preventing DocRaptor from fetching placeholder/random images.

    Pass 2 — Substitute {{key}} tokens.
              • section_*_html keys  →  raw HTML (NOT escaped)
              • All other keys        →  HTML-escaped plain text
              • Unknown keys          →  empty string
    """
    # ── Pass 1: conditional blocks ────────────────────────────────────────────
    def _resolve_if(m: re.Match) -> str:
        key     = m.group(1).strip()
        content = m.group(2)
        val     = variables.get(key, "")
        return content if (val and str(val).strip()) else ""

    result = re.sub(
        r"\{\{#if\s+([\w]+)\}\}(.*?)\{\{/if\}\}",
        _resolve_if,
        template_html,
        flags=re.DOTALL,
    )

    # ── Pass 2: token substitution ────────────────────────────────────────────
    def _replace_token(m: re.Match) -> str:
        key = m.group(1).strip()
        val = variables.get(key)

        if val is None:
            return ""

        val_str = val if isinstance(val, str) else str(val)

        # RAW injection for pre-rendered HTML sections
        if _is_raw_html_key(key):
            return val_str

        # Plain-text escaping for everything else
        return _safe_escape(val_str)

    result = re.sub(r"\{\{([\w]+)\}\}", _replace_token, result)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# DOCRAPTOR SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class DocRaptorService:

    TEMPLATES_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
    )

    TEMPLATE_REGISTRY = {
        "modern-guide": "Template.html",
        "brand-assets": "BrandAssets.html",
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
        # 1. Load template file
        path = self._get_template_path(template_id)
        if not os.path.exists(path):
            return {
                "success": False,
                "error":   f"Template file not found: {path}",
                "details": f"Checked: {path}",
            }

        with open(path, "r", encoding="utf-8") as f:
            template_html = f.read()

        # 2. Render — section_*_html vars are injected as raw HTML
        rendered_html = render_template(template_html, variables)

        # 3. Sanity check
        raw_tag_count = rendered_html.count("&lt;p&gt;") + rendered_html.count("&lt;h3&gt;")
        if raw_tag_count > 5:
            logger.error(
                f"render_template produced {raw_tag_count} escaped HTML tags — "
                "section_*_html vars were NOT injected as raw HTML. "
                "Check that _is_raw_html_key() matches your variable names."
            )

        real_tag_count = rendered_html.count("<p>") + rendered_html.count("<h3>")
        logger.info(f"Rendered HTML | real_tags={real_tag_count} | escaped_tags={raw_tag_count} | length={len(rendered_html):,}")

        # 4. Send to DocRaptor
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
                    "test":             self.test_mode, # Use configured test mode
                    "prince_options": {
                        "media":   "print",
                        "baseurl": getattr(settings, "SITE_URL", "https://www.kyro.com"),
                    },
                },
            }

            logger.info(f"→ DocRaptor | test={self.test_mode} | html={len(rendered_html):,} chars")

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

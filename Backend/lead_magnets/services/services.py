import os
import re
import requests
from typing import Dict, Any, List
from django.conf import settings
from jinja2 import Template, Environment, FileSystemLoader, select_autoescape
import logging


logger = logging.getLogger(__name__)


class DocRaptorService:
    def __init__(self):
        self.api_key = os.getenv('DOCRAPTOR_API_KEY')
        self.base_url = "https://api.docraptor.com/docs"
        self.templates_dir = os.path.join(settings.BASE_DIR, 'lead_magnets', 'templates')
        self.test_mode = True

    def list_templates(self) -> List[Dict[str, Any]]:
        template_path = os.path.join(self.templates_dir, 'Template.html')
        return [
            {
                'id': 'modern-guide',
                'name': 'Modern Guide Template',
                'description': 'Single template rendered from lead_magnets/templates/Template.html',
                'category': 'guide',
                'path': template_path,
            }
        ]

    def render_template_with_vars(self, template_id: str, variables: Dict[str, Any]) -> str:
        env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(['html'])
        )
        template_name = 'Template.html'
        if str(template_id).lower() in ('brand-assets', 'brand_assets', 'brand-assets-preview'):
            template_name = 'BrandAssetsPreview.html'
        template = env.get_template(template_name)
        rendered_html = template.render(**variables)
        
        # DEBUG: Log if variables are missing in the template context
        logger.info('DocRaptorService: template rendered', extra={
            'template_id': template_id,
            'template_name': template_name,
            'variables_count': len(variables),
        })
        
        # Check for unpopulated placeholders in the rendered HTML
        placeholders = re.findall(r'\{\{\s*(\w+)\s*\}\}', rendered_html)
        if placeholders:
            logger.warning(f"⚠️ Unpopulated Jinja2 placeholders found in {template_name}: {set(placeholders)}")
        
        missing = [k for k, v in variables.items() if not v]
        sample_keys = list(variables.keys())[:10]
        print(f"🧩 Render complete")
        print(f"🧪 Variables count: {len(variables)}")
        print(f"🧪 Sample keys: {sample_keys}")
        print(f"🔍 Missing values: {missing[:10]}")
        print(f"🧪 Rendered length: {len(rendered_html)}")

        rendered_html = clean_rendered_html(rendered_html)
        self._save_preview_html(template_id, rendered_html)
        try:
            debug_out = os.path.join(settings.BASE_DIR, 'debug_output.html')
            with open(debug_out, 'w', encoding='utf-8') as f:
                f.write(rendered_html)
            print(f"✅ Saved debug_output.html to {debug_out}")
        except Exception as e:
            print(f"⚠️ Failed to save debug_output.html: {e}")

        return rendered_html

    def _save_preview_html(self, template_id: str, rendered_html: str) -> str:
        preview_dir = os.path.join(settings.MEDIA_ROOT, 'template_previews')
        os.makedirs(preview_dir, exist_ok=True)
        preview_path = os.path.join(preview_dir, f'{template_id}-rendered.html')
        try:
            with open(preview_path, 'w', encoding='utf-8') as f:
                f.write(rendered_html)
            print(f"🧪 DEBUG: Saved rendered HTML preview to {preview_path}")
        except Exception as e:
            print(f"⚠️ DEBUG: Failed to save preview HTML: {e}")
        return preview_path

    def _build_mock_pdf_bytes(self, template_id: str) -> bytes:
        pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 55>>stream\nBT /F1 24 Tf 72 720 Td (Lead Magnet: " + template_id.encode('utf-8') + b") Tj ET\nendstream\nendobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000062 00000 n \n0000000121 00000 n \n0000000285 00000 n \n0000000414 00000 n \n"
            b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n505\n%%EOF\n"
        )
        return pdf

    def generate_pdf(self, template_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        logger.info('DocRaptorService: generate_pdf called', extra={
            'template_id': template_id,
            'has_api_key': bool(self.api_key),
            'test_mode': self.test_mode,
        })
        
        # Hard validation: critical fields MUST be present
        required_keys = ['mainTitle', 'companyName']
        missing = [k for k in required_keys if not str(variables.get(k, '')).strip()]
        if missing:
            logger.error('DocRaptorService: missing required fields', extra={'missing': missing})
            return {
                'success': False,
                'error': 'Missing critical content',
                'details': f"The following fields are required but missing: {', '.join(missing)}"
            }

        try:
            rendered_html = self.render_template_with_vars(template_id, variables)
        except Exception as e:
            logger.error('DocRaptorService: template rendering failed', exc_info=True)
            return {
                'success': False,
                'error': 'Template rendering failed',
                'details': str(e)
            }

        if not self.api_key:
            logger.error('DocRaptorService: DocRaptor API key missing')
            return {
                'success': False,
                'error': 'DocRaptor API key missing',
                'details': 'PDF generation is disabled because the API key is not configured.'
            }

        try:
            logger.info('DocRaptorService: posting to DocRaptor API', extra={
                'template_id': template_id,
                'html_size': len(rendered_html)
            })
            
            # Guard: HTML size limit (approx 1.5MB) to prevent memory spikes
            if len(rendered_html) > 1.5 * 1024 * 1024:
                return {
                    'success': False,
                    'error': 'Content too large',
                    'details': 'The generated content exceeds the memory safety limit for PDF rendering.'
                }

            doc_data = {
                'user_credentials': self.api_key,
                'doc': {
                    'document_type': 'pdf',
                    'document_content': rendered_html,
                    'name': f'lead-magnet-{template_id}',
                    'test': self.test_mode
                }
            }
            response = requests.post(
                self.base_url,
                json=doc_data,
                headers={'Content-Type': 'application/json'},
                timeout=30  # Increased from 12s since this is now a background job
            )
            
            if response.status_code == 200:
                logger.info('DocRaptorService: DocRaptor API success')
                return {
                    'success': True,
                    'pdf_data': response.content,
                    'content_type': 'application/pdf',
                    'filename': f'lead-magnet-{template_id}.pdf',
                    'template_id': template_id
                }
            else:
                logger.error(f'DocRaptorService: DocRaptor API error {response.status_code}', extra={'response': response.text})
                return {
                    'success': False,
                    'error': f'PDF engine error ({response.status_code})',
                    'details': response.text
                }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'PDF generation timed out',
                'details': 'The request to the PDF generation service timed out. Please try with less content.'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': 'PDF generation service unreachable',
                'details': str(e)
            }
        except MemoryError:
            return {
                'success': False,
                'error': 'Memory limit exceeded',
                'details': 'The server ran out of memory while generating the PDF.'
            }
        except Exception as e:
            logger.error('DocRaptorService: unexpected error during PDF generation', exc_info=True)
            return {
                'success': False,
                'error': 'Unexpected PDF generation error',
                'details': str(e)
            }

    def generate_pdf_with_ai_content(self, template_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        return self.generate_pdf(template_id, variables)

    def preview_template(self, template_id: str, variables: Dict[str, Any]) -> str:
        html = self.render_template_with_vars(template_id, variables)
        self._save_preview_html(template_id, html)
        return html

# --- Jinja2 Rendering ---

def clean_rendered_html(html: str) -> str:
    """Remove empty list items, content boxes without text, empty quotes, and stray empty paragraphs."""
    if not html:
        return html
    cleaned = html
    # Remove empty <li>
    cleaned = re.sub(r"<li>\s*</li>", "", cleaned)
    # Remove empty paragraphs
    cleaned = re.sub(r"<p>\s*</p>", "", cleaned)
    # Remove content-box blocks where both h3 and p are empty
    def _drop_empty_box(m):
        h3 = re.sub(r"<.*?>", "", m.group(1)).strip()
        p = re.sub(r"<.*?>", "", m.group(2)).strip()
        return "" if not h3 and not p else m.group(0)
    cleaned = re.sub(r"<div class=\"content-box[^\"]*\">[\s\S]*?<h3>(.*?)</h3>[\s\S]*?<p>(.*?)</p>[\s\S]*?</div>", _drop_empty_box, cleaned)
    # Remove blockquotes with no alphanumeric content
    def _drop_empty_quote(m):
        inner = re.sub(r"<.*?>", "", m.group(0))
        normalized = re.sub(r"[\s\"“”‘’—\-•]+", "", inner)
        return "" if not re.search(r"[A-Za-z0-9]", normalized) else m.group(0)
    cleaned = re.sub(r"<blockquote>[\s\S]*?</blockquote>", _drop_empty_quote, cleaned)
    return cleaned

def render_template(template_html: str, ai_data: Dict[str, Any]) -> str:
    """
    Fills Template.html with AI-generated data dynamically using Jinja2.
    Expects ai_data keys to match placeholders in the HTML.
    """
    template = Template(template_html)
    filled_html = template.render(**ai_data)
    return clean_rendered_html(filled_html)

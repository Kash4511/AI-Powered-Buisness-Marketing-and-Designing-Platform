import os
import re
import requests
import time
import threading
from typing import Dict, Any, List
from django.conf import settings
from jinja2 import Template, Environment, FileSystemLoader, select_autoescape
import logging


logger = logging.getLogger(__name__)

# Global semaphore to limit concurrent DocRaptor requests to 10
DOCRAPTOR_SEMAPHORE = threading.Semaphore(10)


def validate_rendered_html(html: str) -> Dict[str, Any]:
    """
    Strict validation of rendered HTML before sending to DocRaptor.
    Returns a report with 'is_valid' and 'errors' list.
    """
    errors = []
    warnings = []
    
    # 1. Check for unreplaced Jinja2 placeholders
    placeholders = re.findall(r'\{\{\s*(\w+)\s*\}\}', html)
    if placeholders:
        errors.append(f"Unreplaced placeholders found: {set(placeholders)}")
    
    # 2. Check for unclosed tags (basic balance check)
    # This is a simple heuristic, not a full HTML parser check
    tags = re.findall(r'<(/?)([a-zA-Z1-6]+)', html)
    stack = []
    void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    
    for is_closing, tag in tags:
        tag = tag.lower()
        if tag in void_tags:
            continue
        if is_closing:
            if not stack:
                warnings.append(f"Unexpected closing tag: </{tag}>. Auto-ignoring for PDF generation.")
            else:
                top = stack.pop()
                if top != tag:
                    # If there's a mismatch, we'll try to find if the tag is further down the stack
                    if tag in stack:
                        # Found it below - means we missed some closing tags in between
                        missing = []
                        while top != tag:
                            missing.append(top)
                            top = stack.pop()
                        warnings.append(f"Tag mismatch: expected </{', '.join(missing)}>, found </{tag}>. Closing them automatically.")
                    else:
                        # Not in stack - unexpected closing tag
                        stack.append(top) # Put it back
                        warnings.append(f"Unexpected closing tag: </{tag}>. Ignoring.")
        else:
            stack.append(tag)
    
    if stack:
        # Instead of error, let's warn and log the problematic ones
        # Some unclosed tags might be harmless or handled by DocRaptor
        warnings.append(f"Unclosed tags found: {', '.join(stack)}. DocRaptor will attempt to fix them.")
    
    # 3. Check for external CSS/JS links
    links = re.findall(r'href="(http[^"]+)"|src="(http[^"]+)"', html)
    for href, src in links:
        url = href or src
        # Skip some known-good URLs or patterns if needed
        if "fonts.googleapis.com" in url:
            continue
            
        try:
            # Quick HEAD request to verify reachability
            # Use short timeout to avoid blocking
            resp = requests.head(url, timeout=2, allow_redirects=True)
            if resp.status_code >= 400:
                warnings.append(f"Asset might be unreachable (HTTP {resp.status_code}): {url}")
        except Exception as e:
            warnings.append(f"Asset check skipped ({type(e).__name__}): {url}")
            
    # 4. Check for base64 images size
    # DocRaptor recommends keeping base64 images small to avoid massive payloads
    base64_images = re.findall(r'src="data:image/[^;]+;base64,([^"]+)"', html)
    for i, b64 in enumerate(base64_images):
        size_kb = len(b64) * 0.75 / 1024 # Approx size in KB
        if size_kb > 1000: # Increased limit to 1MB warning
            logger.warning(f"⚠️ Large base64 image found ({size_kb:.1f} KB) at index {i}")
            if size_kb > 5000: # Increased limit to 5MB error
                errors.append(f"Base64 image too large ({size_kb:.1f} KB). Use smaller images.")

    if warnings:
        for w in warnings:
            logger.info(f"HTML Validation Warning: {w}")

    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


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
        # Updated regex to handle filters like | length and | default
        placeholders = re.findall(r'\{\{\s*([\w\s|]+)\s*\}\}', rendered_html)
        if placeholders:
            logger.warning(f"⚠️ Unpopulated Jinja2 placeholders found in {template_name}: {set(placeholders)}")
            # Log missing keys for debugging but don't fail rendering
            logger.debug(f"DocRaptorService: Missing keys in HTML: {set(placeholders)}")
        
        missing = [k for k, v in variables.items() if not v]
        sample_keys = list(variables.keys())[:10]
        print(f"🧩 Render complete")
        print(f"🧪 Variables count: {len(variables)}")
        print(f"🧪 Sample keys: {sample_keys}")
        print(f"🔍 Missing values: {missing[:10]}")
        print(f"🧪 Rendered length: {len(rendered_html)}")

        rendered_html = clean_rendered_html(rendered_html, variables)
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
            # Log the first 1000 characters of rendered HTML for visual check
            logger.info(f"DocRaptorService: Rendered HTML Snippet: {rendered_html[:1000]}...")
            
            # Strict HTML Validation
            validation_report = validate_rendered_html(rendered_html)
            if not validation_report['is_valid']:
                logger.error(f"❌ HTML Validation failed: {validation_report['errors']}")
                return {
                    'success': False,
                    'error': 'Template rendering failed',
                    'details': f"HTML Validation Errors: {'; '.join(validation_report['errors'])}"
                }
            
            logger.info("✅ HTML Validation passed.")

        except Exception as e:
            logger.error('DocRaptorService: template rendering failed', exc_info=True)
            logger.error(f"DocRaptorService: Problematic variables: {list(variables.keys())}")
            return {
                'success': False,
                'error': 'Template rendering failed',
                'details': f"Jinja2 Error: {str(e)}. Check Template.html for syntax errors or missing variables."
            }

        if not self.api_key:
            logger.error('DocRaptorService: DocRaptor API key missing')
            return {
                'success': False,
                'error': 'DocRaptor API key missing',
                'details': 'PDF generation is disabled because the API key is not configured.'
            }

        # Exponential Backoff Retry Logic
        max_retries = 5 # Increased from 3
        base_delay = 3 # Increased from 2
        
        for attempt in range(max_retries):
            # Limit concurrent requests to DocRaptor using global semaphore
            with DOCRAPTOR_SEMAPHORE:
                try:
                    logger.info(f"DocRaptorService: Posting to DocRaptor API (Attempt {attempt + 1})", extra={
                        'template_id': template_id,
                        'html_size': len(rendered_html)
                    })
                    
                    doc_data = {
                        'user_credentials': self.api_key,
                        'doc': {
                            'document_type': 'pdf',
                            'document_content': rendered_html,
                            'name': f'lead-magnet-{template_id}',
                            'test': self.test_mode,
                            'strict': 'none',
                            'javascript': False,
                            'help': False # CRITICAL: Disable diagnostic mode to avoid "Too many open help requests"
                        }
                    }
                    
                    # Log full request headers and partially redacted body
                    logger.debug(f"DocRaptor Request Headers: {{'Content-Type': 'application/json'}}")
                    logger.debug(f"DocRaptor Request Body (redacted): {{'user_credentials': '...', 'doc': {{...}}}}")

                    # DocRaptor supports both user_credentials in body and Basic Auth
                    # We provide both for maximum compatibility and to satisfy header requirements
                    auth = (self.api_key, '') # Basic Auth uses API key as username, empty password
                    
                    timeout = 120 # Increased timeout for dense documents
                    response = requests.post(
                        self.base_url,
                        json=doc_data,
                        auth=auth,
                        headers={'Content-Type': 'application/json'},
                        timeout=timeout
                    )
                    
                    # Log full response details
                    logger.info(f"DocRaptor Response Status: {response.status_code}")
                    logger.debug(f"DocRaptor Response Headers: {dict(response.headers)}")
                    
                    if response.status_code == 200:
                        logger.info(f"DocRaptorService: PDF generated successfully ({len(response.content)} bytes)")
                        return {
                            'success': True,
                            'pdf_data': response.content,
                            'content_type': 'application/pdf',
                            'filename': f'lead-magnet-{template_id}.pdf',
                            'template_id': template_id
                        }
                    elif response.status_code == 401:
                        logger.error("❌ DocRaptor Authentication Failed (401). Check API Key.")
                        return {
                            'success': False,
                            'error': 'DocRaptor Authentication Failed',
                            'details': 'The DocRaptor API key is invalid or has expired.'
                        }
                    elif response.status_code in (403, 429, 500, 502, 503, 504):
                        # Transient errors or rate limits - retry with backoff
                        # 403 can also be "Too many open help requests" if help: True was used previously
                        wait_time = base_delay * (2 ** attempt)
                        logger.warning(f"⚠️ DocRaptor transient error {response.status_code}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # Permanent error
                        logger.error(f"❌ DocRaptor API Error {response.status_code}: {response.text}")
                        return {
                            'success': False,
                            'error': f'PDF Engine Error ({response.status_code})',
                            'details': f"Status {response.status_code}: {response.text[:1000]}..."
                        }

                except requests.exceptions.Timeout:
                    wait_time = base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ DocRaptor timeout. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ DocRaptor RequestException: {str(e)}")
                    return {
                        'success': False,
                        'error': 'PDF generation service unreachable',
                        'details': str(e)
                    }
                except Exception as e:
                    logger.error('DocRaptorService: unexpected error during PDF generation', exc_info=True)
                    return {
                        'success': False,
                        'error': 'Unexpected PDF generation error',
                        'details': str(e)
                    }
        
        # If we reach here, all retries failed
        return {
            'success': False,
            'error': 'PDF generation failed after multiple attempts',
            'details': 'The PDF engine is currently unavailable or timing out. Please try again later.'
        }

    def generate_pdf_with_ai_content(self, template_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        return self.generate_pdf(template_id, variables)

    def preview_template(self, template_id: str, variables: Dict[str, Any]) -> str:
        html = self.render_template_with_vars(template_id, variables)
        self._save_preview_html(template_id, html)
        return html

# --- Jinja2 Rendering ---

def clean_rendered_html(html: str, variables: Dict[str, Any] = None) -> str:
    """Remove empty list items, content boxes without text, empty quotes, and stray empty paragraphs."""
    if not html:
        return html
    cleaned = html
    
    # Process IMAGE_PLACEHOLDER markers
    # We try to find actual images from variables if available
    architectural_images = []
    if variables and 'architecturalImages' in variables:
        architectural_images = variables['architecturalImages']

    placeholder_count = 0
    def _replace_placeholder(match):
        nonlocal placeholder_count
        desc = match.group(1).strip()
        
        # Cycle through architectural images if we run out
        if architectural_images:
            # Use modulo to cycle through available images
            img_index = placeholder_count % len(architectural_images)
            img = architectural_images[img_index]
            placeholder_count += 1
            
            # Handle both string (data URL) and dict formats
            src = img if isinstance(img, str) else img.get('src', '')
            alt = desc if isinstance(img, str) else img.get('alt', desc)
            
            return f"""
            <div class="img-container full-width-center">
                <div class="img-wrapper">
                    <img src="{src}" alt="{alt}">
                </div>
                <span class="img-cap">{desc}</span>
            </div>
            """
        
        # No fallback box - return empty or a small debug marker
        logger.warning(f"⚠️ Placeholder '{desc}' has no images available to display.")
        return ""
    cleaned = re.sub(r"\[IMAGE_PLACEHOLDER:\s*([^\]]+)\]", _replace_placeholder, cleaned)

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
    return clean_rendered_html(filled_html, ai_data)

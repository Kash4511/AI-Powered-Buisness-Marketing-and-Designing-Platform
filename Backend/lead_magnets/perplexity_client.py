import os
from pathlib import Path
import json
import requests
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


class PerplexityClient:
    """Client for interacting with Perplexity AI API for lead magnet content generation"""
    
    def __init__(self):
        # Ensure .env is loaded in server context
        if load_dotenv:
            env_path = Path(__file__).resolve().parents[1] / '.env'
            try:
                load_dotenv(env_path)
            except Exception:
                pass
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        self.base_url = "https://api.perplexity.ai/chat/completions"
        print(f"DEBUG: PerplexityClient initialized; key present: {bool(self.api_key)}")
        
    def generate_lead_magnet_json(self, user_answers: Dict[str, Any], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            print("❌ PERPLEXITY_API_KEY missing")
            raise Exception("PERPLEXITY_API_KEY is not configured; cannot generate AI content. Please add PERPLEXITY_API_KEY=your_key_here to your Backend/.env file")

        max_retries = 2
        retry_count = 0
        models_to_try = ["sonar-pro", "sonar"]

        while retry_count <= max_retries:
            model_to_use = models_to_try[1] if retry_count == max_retries else models_to_try[0]
            try:
                if retry_count > 0:
                    print(f"🔄 Retrying AI content generation (attempt {retry_count + 1}/{max_retries + 1}) with model: {model_to_use}...")
                else:
                    print(f"Generating AI content with model: {model_to_use}...")

                response = requests.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    json={
                        "model": model_to_use,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert content creator specializing in professional lead magnets. Generate comprehensive, valuable content in strict JSON format. Your response must be valid JSON only, no other text."
                            },
                            {
                                "role": "user",
                                "content": self._create_content_prompt(user_answers, firm_profile)
                            }
                        ],
                        "max_tokens": 4000,
                        "temperature": 0.7
                    },
                    timeout=20
                )
                break
            except requests.exceptions.Timeout:
                retry_count += 1
                if retry_count > max_retries:
                    print("❌ Perplexity API timeout after multiple attempts")
                    raise Exception("Perplexity API timeout after multiple attempts (20s each)")
                else:
                    print(f"⚠️ API timeout on attempt {retry_count}, retrying...")
                    continue
            except requests.exceptions.RequestException as e:
                print(f"❌ Perplexity API request error: {e}")
                raise Exception(f"Perplexity API request error: {e}")
            except Exception as e:
                print(f"❌ Error calling Perplexity API: {str(e)}")
                raise

        print(f"Perplexity response status: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Perplexity API error: {response.status_code} - {response.text}")
            raise Exception(f"Perplexity API error: {response.status_code} - {response.text}")

        result = response.json()
        message_content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        json_content = self._extract_json_from_markdown(message_content)
        try:
            content = json.loads(json_content)
            return content
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON from Perplexity response: {e}")
            print(f"Raw content: {repr(message_content)}")
            print(f"Extracted JSON: {repr(json_content)}")
            raise Exception("Invalid JSON returned from Perplexity API")

    def _extract_json_from_markdown(self, content: str) -> str:
        """
        Extract JSON from markdown code blocks.
        Handles formats like:
        ```json
        { ... }
        ```
        or just plain JSON
        """
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Check if content is wrapped in markdown code blocks
        if content.startswith('```'):
            # Find the start and end of the code block
            lines = content.split('\n')
            start_idx = 0
            end_idx = len(lines)
            
            # Find the first line that starts with ```
            for i, line in enumerate(lines):
                if line.strip().startswith('```'):
                    start_idx = i + 1
                    break
            
            # Find the last line that starts with ```
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip().startswith('```'):
                    end_idx = i
                    break
            
            # Extract content between code blocks
            json_lines = lines[start_idx:end_idx]
            return '\n'.join(json_lines)
        
        # If not wrapped in code blocks, return as-is
        return content

    def debug_ai_content(self, ai_content: Dict[str, Any]):
        """Debug function to see what the AI actually returned"""
        try:
            print("🔍 DEBUG AI CONTENT STRUCTURE:")
            print(f"Style: {ai_content.get('style', {})}")
            print(f"Cover: {ai_content.get('cover', {})}")
            print(f"Contents items: {ai_content.get('contents', {}).get('items', [])}")
            sections = ai_content.get('sections', [])
            print(f"Number of sections: {len(sections)}")
            for i, section in enumerate(sections):
                title = section.get('title', 'NO TITLE')
                content = section.get('content', 'NO CONTENT')
                print(f"Section {i}: {title}")
                print(f"  Content: {str(content)[:100]}...")
                print(f"  Subsections: {len(section.get('subsections', []))}")
            print(f"Contact: {ai_content.get('contact', {})}")
        except Exception as e:
            print(f"🔴 DEBUG AI CONTENT ERROR: {e}")


    def _is_meaningless(self, value: Any) -> bool:
        """Strict check for meaningless or placeholder inputs."""
        if not value:
            return True
        v = str(value).strip()
        if not v:
            return True
        
        # Too short to carry semantic meaning (e.g. "h", "hh", "k", "m")
        if len(v) < 3:
            return True
            
        # Common placeholder patterns
        lowered = v.lower()
        placeholders = {
            "test", "testing", "hh", "h", "k", "m", "d", "dd", "none", "na", "n/a", 
            "empty", "placeholder", "asdf", "qwerty", "ok", "yes", "no", ".", "..", "..."
        }
        if lowered in placeholders:
            return True
            
        # Random character strings (low vowel count or weird consonant clusters)
        if len(v) > 4 and not re.search(r'[aeiouy]', lowered):
            return True
            
        return False

    def _create_content_prompt(self, user_answers: Dict[str, Any], firm_profile: Dict[str, Any]) -> str:
        """
        Build a strict, dynamic prompt that forces the AI to generate
        complete, content-heavy JSON using the provided firm profile and
        user answers. The AI MUST return valid JSON only.
        """
        # Filter meaningless user answers
        filtered_answers = {}
        for k, v in user_answers.items():
            if not self._is_meaningless(v):
                filtered_answers[k] = v
            else:
                # Still include the key but with None to signal it should be ignored
                filtered_answers[k] = None

        # Firm profile inputs
        firm_name = (firm_profile.get('firm_name') or '').strip()
        work_email = (firm_profile.get('work_email') or '').strip()
        phone = (firm_profile.get('phone_number') or '').strip()
        website = (firm_profile.get('firm_website') or '').strip()
        tagline = (firm_profile.get('tagline') or '').strip()
        logo_url = (filtered_answers.get('brand_logo_url') or firm_profile.get('logo_url') or '').strip()

        # Brand colors: prefer user_answers brand_* then firm_profile brand_*, then generic; no hardcoded defaults
        primary_color = (
            (filtered_answers.get('brand_primary_color') or '').strip()
            or (firm_profile.get('brand_primary_color') or '').strip()
            or (firm_profile.get('primary_brand_color') or '').strip()
            or (firm_profile.get('primary_color', '') or '').strip()
        )
        secondary_color = (
            (filtered_answers.get('brand_secondary_color') or '').strip()
            or (firm_profile.get('brand_secondary_color') or '').strip()
            or (firm_profile.get('secondary_brand_color') or '').strip()
            or (firm_profile.get('secondary_color', '') or '').strip()
        )
        accent_color = (
            (filtered_answers.get('brand_accent_color') or '').strip()
            or (firm_profile.get('brand_accent_color') or '').strip()
            or (firm_profile.get('accent_brand_color') or '').strip()
            or (firm_profile.get('accent_color', '') or '').strip()
        )

        # User-provided context
        main_topic = (filtered_answers.get('main_topic') or '').strip()
        lead_magnet_type = (filtered_answers.get('lead_magnet_type') or '').strip()
        target_audience = filtered_answers.get('target_audience') or []
        desired_outcome = (filtered_answers.get('desired_outcome') or '').strip()
        audience_pain_points = filtered_answers.get('audience_pain_points') or []
        call_to_action = (filtered_answers.get('call_to_action') or '').strip()
        industry = (filtered_answers.get('industry') or '').strip()

        # AI customization: style should follow the topic unless a specific industry is provided
        if industry:
            prompt_style = f"Expert level, professional {industry} style. High value, actionable content."
        else:
            prompt_style = "Professional, authoritative, and expert level. Focus on providing high-value insights."

        # Compose a strict instruction.
        prompt = (
            "You are a senior expert content strategist. Generate a high-value, professional lead magnet in JSON format. "
            "STRICT RULES:\n"
            "1. If a user input field is provided but marked as null or empty, IGNORE it and generate the best expert content based on the 'main_topic' and 'lead_magnet_type'.\n"
            "2. If a user input field is meaningful, ADAPT it professionally into the content. Do not just copy-paste; elevate it.\n"
            "3. Content must be expert-level, topic-relevant, and highly professional. No generic or placeholder text.\n"
            "4. Output MUST be valid JSON ONLY. No prose, no markdown code blocks.\n\n"
            "Style: " + prompt_style + "\n\n" +
            "Inputs:\n" +
            json.dumps({
                "firm_profile": {
                    "firm_name": firm_name,
                    "work_email": work_email,
                    "phone_number": phone,
                    "firm_website": website,
                    "tagline": tagline,
                    "logo_url": logo_url,
                    "brand_primary_color": primary_color,
                    "brand_secondary_color": secondary_color,
                    "brand_accent_color": accent_color,
                },
                "user_answers": {
                    "main_topic": main_topic,
                    "lead_magnet_type": lead_magnet_type,
                    "target_audience": target_audience,
                    "desired_outcome": desired_outcome,
                    "audience_pain_points": audience_pain_points,
                    "call_to_action": call_to_action,
                    "industry": industry,
                }
            }, ensure_ascii=False) + "\n\n" +
            "Output Schema (keys must match EXACTLY):\n" +
            json.dumps({
                "style": {
                    "primary_color": "<hex or CSS color, use brand_primary_color>",
                    "secondary_color": "<hex or CSS color, use brand_secondary_color>",
                    "accent_color": "<hex or CSS color, use brand_accent_color>"
                },
                "brand": {
                    "logo_url": "<use provided logo_url if available>"
                },
                "cover": {
                    "title": "<compose from lead_magnet_type + main_topic>",
                    "subtitle": "<use desired_outcome; summarize value proposition>",
                    "company_name": "<firm_name>",
                    "company_tagline": "<tagline>"
                },
                "terms": {
                    "title": "Terms of Use",
                    "summary": "<1 sentence>",
                    "paragraphs": [
                        "<2–3 sentences>",
                        "<2–3 sentences>",
                        "<2–3 sentences>"
                    ]
                },
                "contents": {
                    "items": ["<6 descriptive items for TOC>"]
                },
                "sections": [
                    {
                        "title": "<Section 1 title>",
                        "content": "<1-2 detailed paragraphs with specific examples>",
                        "subsections": [
                            {"title": "<Sub 1>", "content": "<2-3 detailed sentences with specific information>"},
                            {"title": "<Sub 2>", "content": "<2-3 detailed sentences with specific information>"}
                        ]
                    },
                    {
                        "title": "<Section 2 title>",
                        "content": "<1-2 detailed paragraphs with specific examples>",
                        "subsections": [
                            {"title": "<Sub 1>", "content": "<2-3 detailed sentences with specific information>"},
                            {"title": "<Sub 2>", "content": "<2-3 detailed sentences with specific information>"}
                        ]
                    },
                    {
                        "title": "<Section 3 title>",
                        "content": "<1-2 detailed paragraphs with specific examples>",
                        "subsections": [
                            {"title": "<Sub 1>", "content": "<2-3 detailed sentences with specific information>"},
                            {"title": "<Sub 2>", "content": "<2-3 detailed sentences with specific information>"}
                        ]
                    },
                    {
                        "title": "<Section 4 title>",
                        "content": "<1-2 detailed paragraphs with specific examples>",
                        "subsections": [
                            {"title": "<Sub 1>", "content": "<2-3 detailed sentences with specific information>"},
                            {"title": "<Sub 2>", "content": "<2-3 detailed sentences with specific information>"}
                        ]
                    },
                    {
                        "title": "<Section 5 title>",
                        "content": "<1-2 detailed paragraphs with specific examples>",
                        "subsections": [
                            {"title": "<Sub 1>", "content": "<2-3 detailed sentences with specific information>"},
                            {"title": "<Sub 2>", "content": "<2-3 detailed sentences with specific information>"}
                        ]
                    }
                ],
                "contact": {
                    "title": "<value-driven CTA headline, not 'Contact us'>",
                    "description": "<2–4 sentences describing a concrete offer tied to pain_points and desired_outcome>",
                    "offer_name": "<short name of the concrete offer (audit, checklist, estimator, framework, or assessment)>",
                    "action_cta": "<1 sentence with a specific next step; avoid generic 'contact us/learn more'>",
                    "phone": "<phone_number>",
                    "email": "<work_email>",
                    "website": "<firm_website>",
                    "differentiator_title": "Why Choose <firm_name>",
                    "differentiator": "<3-5 sentences highlighting unique value with specific examples>"
                }
            }, ensure_ascii=False) + "\n\n" +
            "Hard Requirements:\n"
            "- Address the target_audience EXCLUSIVELY. All content must be tailored to their specific pain_points and desired_outcomes.\n"
            "- Use firm_name, work_email, phone_number, firm_website, tagline EXACTLY as provided.\n"
            "- Use brand colors EXACTLY as provided (primary, secondary, accent). If any input color is missing, set that field to an empty string rather than inventing a color.\n"
            "- Include logo_url if provided; else set to an empty string.\n"
            "- Generate concise sections: each section has 1 paragraph; each subsection 1–2 sentences.\n"
            "- Terms must include a summary and 3 paragraphs (2–3 sentences each).\n"
            "- Contents.items must have 6 descriptive entries aligned to the sections.\n"
            "- The contact section must describe a specific offer (audit, checklist, estimator, framework, or assessment) that is clearly linked to main_topic and audience_pain_points.\n"
            "- contact.offer_name and contact.action_cta must be specific and must not use generic phrases like 'Contact us', 'Get in touch', or 'Learn more'.\n"
            "- contact.description must clearly state what the reader receives, who it is for, and the outcome, grounded in desired_outcome and audience_pain_points.\n"
            "- NO extra text outside JSON, NO Markdown, NO comments.\n"
            "- Do NOT use any placeholder like 'TEST DOCUMENT'.\n"
        )

        return prompt
        
    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Optional[Dict[str, Any]] = None,
        user_answers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        firm_profile = firm_profile or {}
        user_answers = user_answers or {}
        style = ai_content.get("style", {})
        cover = ai_content.get("cover", {})
        contents = ai_content.get("contents", {})
        sections = ai_content.get("sections", [])
        contact = ai_content.get("contact", {})
        terms = ai_content.get("terms", {})
        brand = ai_content.get("brand", {})

        # Colors: prefer AI style, fallback to firm_profile brand, then sensible defaults
        primary_color = (
            style.get("primary_color")
            or firm_profile.get("primary_brand_color")
            or firm_profile.get("brand_primary_color")
            or firm_profile.get("primary_color", "")
            or "#8B4513"
        )
        secondary_color = (
            style.get("secondary_color")
            or firm_profile.get("secondary_brand_color")
            or firm_profile.get("brand_secondary_color")
            or firm_profile.get("secondary_color", "")
            or "#D2691E"
        )
        accent_color = (
            style.get("accent_color")
            or firm_profile.get("accent_color")
            or firm_profile.get("brand_accent_color", "")
            or "#F4A460"
        )

        cream_color = (
            firm_profile.get("cream_color")
            or firm_profile.get("background_color")
            or "#F6F1EB"
        )
        cream_dark_color = (
            firm_profile.get("cream_dark_color")
            or firm_profile.get("background_dark_color")
            or "#E0D4C3"
        )
        ink_color = (
            firm_profile.get("ink_color")
            or firm_profile.get("text_color")
            or "#111111"
        )
        ink_mid_color = (
            firm_profile.get("ink_mid_color")
            or firm_profile.get("text_color_muted")
            or "#222222"
        )
        ink_light_color = (
            firm_profile.get("ink_light_color")
            or firm_profile.get("text_color_subtle")
            or "#666666"
        )
        rule_color = (
            firm_profile.get("rule_color")
            or firm_profile.get("divider_color")
            or cream_dark_color
        )

        # Firm info: prefer AI cover/contact, fallback to firm_profile
        company_name = cover.get("company_name") or firm_profile.get("firm_name", "")
        company_subtitle = cover.get("company_tagline") or firm_profile.get("tagline", "")
        logo_url = brand.get("logo_url") or firm_profile.get("logo_url", "")
        email = contact.get("email") or firm_profile.get("work_email", "")
        phone = contact.get("phone") or firm_profile.get("phone_number", "")
        website = contact.get("website") or firm_profile.get("firm_website", "")

        ua_main_topic = (user_answers.get("main_topic") or "").strip()
        ua_target_audience = user_answers.get("target_audience")
        ua_pain_points = user_answers.get("audience_pain_points") or user_answers.get("pain_points")
        ua_desired_outcome = (user_answers.get("desired_outcome") or "").strip()
        ua_call_to_action = (user_answers.get("call_to_action") or "").strip()
        ua_industry = (user_answers.get("industry") or firm_profile.get("industry") or "").strip()

        # Terms and contents
        terms_title = terms.get("title", "Terms of Use")
        terms_summary = terms.get("summary", "")
        terms_paragraphs = terms.get("paragraphs", [])
        content_items = contents.get("items", [])

        # Helper functions
        def get_section(idx):
            return sections[idx] if idx < len(sections) else {"title": "", "content": "", "subsections": []}

        def get_sub(section_idx, sub_idx):
            sec = get_section(section_idx)
            subs = sec.get("subsections", [])
            return subs[sub_idx] if sub_idx < len(subs) else {"title": "", "content": ""}

        # Content length limiters to prevent overflow
        def truncate_text(text: str, max_chars: int) -> str:
            """Truncate text to prevent page overflow. Always return a string, cutting on word boundaries when possible."""
            if not text:
                return ""
            text = str(text)
            if len(text) <= max_chars:
                return text
            # Find last complete sentence within limit
            truncated = text[:max_chars]
            last_period = truncated.rfind('.')
            last_exclamation = truncated.rfind('!')
            last_question = truncated.rfind('?')
            last_sentence_end = max(last_period, last_exclamation, last_question)

            # Try to end at a sentence boundary if it's reasonably close to our limit
            if last_sentence_end > max_chars * 0.6:
                return text[:last_sentence_end + 1].strip()
                
            # Always cut at word boundaries to avoid mid-word truncation
            last_space = truncated.rfind(' ')
            if last_space > 0:  # Ensure we found a space
                # Try to complete by expanding to the next sentence end within a reasonable buffer
                next_zone = text[max_chars:]
                m = re.search(r"[.!?]", next_zone)
                if m:
                    return text[:max_chars + m.start() + 1].strip()
                # Otherwise, end cleanly at word boundary without ellipsis
                return truncated[:last_space].rstrip()
                
            # Absolute fallback: no ellipsis to avoid abrupt stops
            return truncated.rstrip()

        def truncate_title(text: str) -> str:
            """Limit title length (~80 chars) but avoid cutting off meaningful phrases"""
            return truncate_text(text, 80)

        def truncate_content(text: str) -> str:
            return truncate_text(text, 520)

        def truncate_subcontent(text: str) -> str:
            return truncate_text(text, 200)

        def truncate_description(text: str) -> str:
            return truncate_text(text, 140)

        def finalize_line(text: str) -> str:
            t = (text or '').strip()
            if not t:
                return ''
            # Remove trailing connectors without an object
            t = re.sub(r"[\s,\-]+(and|or|with)\s*$", "", t, flags=re.IGNORECASE)
            # Remove incomplete trailing clause like "and stay" / "and improve"
            t = re.sub(r"\s+(and|or|with)\s+[A-Za-z]{1,15}\s*$", "", t, flags=re.IGNORECASE)
            t = re.sub(r"[\s,\-]+$", "", t)
            if not re.search(r"[.!?]$", t):
                t = t + "."
            return t

        # --- Heading/content alignment & terminology normalization helpers ---
        STOPWORDS = set(
            "a an the for and or with of in on to by from at into over under about after before during through across against between toward toward within without".split()
        )

        def keywords_from_title(title: str) -> List[str]:
            t = (title or "").lower()
            # Keep alphanumerics, split on non-letters
            tokens = re.split(r"[^a-z0-9]+", t)
            # Remove short words and stopwords
            return [w for w in tokens if len(w) > 3 and w not in STOPWORDS]

        def contains_any_keyword(text: str, kws: List[str]) -> bool:
            if not text or not kws:
                return False
            t = (text or "").lower()
            return any(re.search(rf"\b{re.escape(k)}\b", t) for k in kws)

        def standardize_sustainable_terms(text: str) -> str:
            t = text or ""
            # Normalize common variants to keep terminology consistent
            t = re.sub(r"\beco[-\s]?friendly\b", "sustainable", t, flags=re.IGNORECASE)
            t = re.sub(r"\bgreen(\s+(home|materials|solutions|upgrades))\b", r"sustainable \1", t, flags=re.IGNORECASE)
            # Collapse redundant repeats like "sustainable, sustainable"
            t = re.sub(r"\b(sustainable)(\s*,\s*\1)+\b", r"\1", t, flags=re.IGNORECASE)
            # Limit frequency without removing meaning: if more than 4 occurrences, reduce extras
            occurrences = [m for m in re.finditer(r"\bsustainable\b", t, flags=re.IGNORECASE)]
            if len(occurrences) > 4:
                # Replace every occurrence beyond the 4th with nothing (keeps grammar generally intact)
                keep = 0
                def repl(m):
                    nonlocal keep
                    keep += 1
                    return m.group(0) if keep <= 4 else ""
                t = re.sub(r"\bsustainable\b", repl, t, flags=re.IGNORECASE)
                # Clean up double spaces from removals
                t = re.sub(r"\s{2,}", " ", t).strip()
            return t

        def derive_title_from_content(content: str) -> str:
            if not content:
                return ""
            first_sentence_match = re.search(r"^(.*?[.!?])\s", content)
            first = first_sentence_match.group(1) if first_sentence_match else content.strip()
            # Keep capitalized words and key nouns/adjectives
            words = re.split(r"\s+", re.sub(r"[^A-Za-z0-9\s]", "", first))
            filtered = [w for w in words if w.lower() not in STOPWORDS]
            phrase = " ".join(filtered[:8]).strip()
            phrase = re.sub(r"\s+", " ", phrase).strip(" -:;")
            return phrase.title() if phrase else "Summary"

        def refine_title_with_content(title: str, content: str) -> str:
            kws = keywords_from_title(title)
            if contains_any_keyword(content, kws):
                return clean_title(title)
            # Mismatch: derive a concise heading from content
            return clean_title(derive_title_from_content(content))

        def harmonize_section(title: str, content: str) -> str:
            # Normalize core content and ensure alignment with heading topic
            norm = normalize_main_content(content, title)
            norm = standardize_sustainable_terms(norm)
            kws = keywords_from_title(title)
            if not contains_any_keyword(norm, kws) and title.strip():
                # Prepend a brief aligning lead
                lead = f"This section focuses on {title.lower()}. "
                norm = lead + norm
            return norm

        def sloganize(text: str) -> str:
            t = (text or '').strip()
            if not t:
                return ''
            m = re.search(r"[.!?]", t)
            if m:
                t = t[:m.start()]
            t = re.sub(r"\s+", " ", t).strip(" -:;,")
            t = truncate_description(t)
            return finalize_line(t)

        def clean_subtitle(text: str) -> str:
            t = (text or '').strip()
            if not t:
                return ''
            # If too short or only punctuation/dots, drop it
            if len(t) <= 2 or all(c in '.,;:!?-' for c in t) or re.fullmatch(r"[.\s-]+", t):
                return ''
            return t

        def detect_generic_cta(text: str) -> bool:
            t = (text or "").strip().lower()
            if not t:
                return True
            if len(t) < 25:
                return True
            generic_phrases = [
                "contact us",
                "get in touch",
                "reach out",
                "learn more",
                "call us today",
                "contact our team",
                "contact kyro",
                "schedule a call",
                "book a call",
                "book a meeting",
                "request more information",
            ]
            for phrase in generic_phrases:
                if phrase in t:
                    return True
            words = t.split()
            if len(words) <= 6 and "@" not in t and "http" not in t:
                return True
            return False

        def audience_phrase(raw) -> str:
            if not raw:
                return ""
            if isinstance(raw, str):
                return raw.strip()
            if isinstance(raw, list):
                parts = [str(x).strip() for x in raw if str(x).strip()]
                return ", ".join(parts)
            return str(raw).strip()

        def pain_points_list(raw) -> List[str]:
            if not raw:
                return []
            if isinstance(raw, str):
                pieces = re.split(r"[;,]", raw)
                return [p.strip() for p in pieces if p.strip()]
            if isinstance(raw, list):
                return [str(p).strip() for p in raw if str(p).strip()]
            return [str(raw).strip()]

        def select_offer_name(topic: str, industry: str) -> str:
            t = (topic or "").lower()
            ind = (industry or "").lower()
            base = t + " " + ind
            if re.search(r"smart home|smart-home|home automation|connected home", base):
                return "Smart Home Cost Audit"
            if re.search(r"sustainable|sustainability|green building|net zero|net-zero|low carbon", base):
                if re.search(r"material", base):
                    return "Material Selection Framework"
                return "Design ROI Estimator"
            if re.search(r"passive house|passivhaus", base):
                return "Energy Savings Assessment"
            if re.search(r"retrofit|renovation|remodel", base):
                return "Project Retrofit Assessment"
            if topic:
                return f"{topic.strip().title()} Strategy Session"
            return "Project Strategy Session"

        def build_value_description(offer_name: str, topic: str, aud_phrase: str, pains: List[str], desired: str) -> str:
            audience_part = f" for {aud_phrase}" if aud_phrase else ""
            topic_part = topic or "your project"
            if pains:
                pp = ", ".join(pains[:3])
                pain_part = f" focusing on challenges like {pp}"
            else:
                pain_part = ""
            outcome_part = desired or "help you move forward with confidence"
            s1 = f"Get a {offer_name}{audience_part} to review your plans for {topic_part}{pain_part}"
            s2 = f"You will walk away with clear, practical next steps designed to {outcome_part}"
            if not re.search(r"[.!?]$", s1):
                s1 += "."
            if not re.search(r"[.!?]$", s2):
                s2 += "."
            return f"{s1} {s2}"

        def build_action_cta(offer_name: str, aud_phrase: str, desired: str, email_value: str, website_value: str, call_text: str) -> str:
            base = (call_text or "").strip()
            if base and not detect_generic_cta(base):
                if not re.search(r"[.!?]$", base):
                    base += "."
                return base
            parts: List[str] = []
            if aud_phrase:
                parts.append(f"If you are {aud_phrase},")
            else:
                parts.append("If this guide resonates with you,")
            parts.append(f"schedule your {offer_name} now")
            contact_bits: List[str] = []
            if email_value:
                contact_bits.append(f"email {email_value}")
            if website_value:
                contact_bits.append(f"visit {website_value}")
            if contact_bits:
                parts.append("– " + " or ".join(contact_bits))
            text = " ".join(parts).strip()
            if desired:
                text = text.rstrip(".")
                text += f" to {desired.strip()}."
            elif not re.search(r"[.!?]$", text):
                text += "."
            return text

        def render_final_cta() -> Dict[str, str]:
            topic = ua_main_topic
            aud_phrase = audience_phrase(ua_target_audience)
            pains = pain_points_list(ua_pain_points)
            desired = ua_desired_outcome
            offer_name_ai = (contact.get("offer_name") or "").strip()
            offer_name_value = offer_name_ai or select_offer_name(topic, ua_industry)
            desc_ai = (contact.get("description") or "").strip()
            title_ai = (contact.get("title") or "").strip()
            action_ai = (contact.get("action_cta") or "").strip()
            combined_ai = " ".join([title_ai, desc_ai, action_ai]).strip()
            is_generic = detect_generic_cta(combined_ai)
            value_desc = build_value_description(offer_name_value, topic, aud_phrase, pains, desired)
            if not is_generic and desc_ai:
                if len(desc_ai.split()) < 25:
                    final_desc = f"{desc_ai.strip()} {value_desc}"
                else:
                    final_desc = desc_ai.strip()
            else:
                final_desc = value_desc
            action_text = build_action_cta(offer_name_value, aud_phrase, desired, email, website, ua_call_to_action)
            diff_ai = (contact.get("differentiator") or "").strip()
            if diff_ai:
                diff_text = diff_ai
            else:
                base_topic = topic or "your project"
                diff_text = f"{offer_name_value} is delivered by {company_name} with a focus on practical, implementable guidance for {base_topic} so you can act quickly and confidently."
            section_title = "Next Step"
            offer_heading = offer_name_value
            return {
                "section_title": section_title,
                "description": final_desc,
                "offer_name": offer_heading,
                "differentiator": diff_text,
                "action_text": action_text,
            }

        ua_description_raw = (user_answers.get("lead_magnet_description") or user_answers.get("description") or "").strip()

        def is_invalid_description(text: str) -> bool:
            t = (text or "").strip()
            if not t:
                return True
            if len(t) < 12:
                return True
            if len(t.split()) <= 3:
                return True
            if not re.search(r"[A-Za-z]", t):
                return True
            low = t.lower()
            bad_tokens = ["hh", "asdf", "lorem ipsum", "lipsum", "placeholder", "tbd", "test", "testing"]
            if any(bt in low for bt in bad_tokens):
                return True
            if re.fullmatch(r"[A-Za-z]{1,4}", t):
                return True
            return False

        def build_professional_description() -> str:
            topic = ua_main_topic or "your next project"
            aud = audience_phrase(ua_target_audience)
            pains = pain_points_list(ua_pain_points)
            desired = ua_desired_outcome or "move from ideas to a confident plan"
            parts: List[str] = []
            intro = "This guide is designed"
            if aud:
                intro += f" for {aud}"
            intro += f" to help you navigate {topic} with clarity"
            parts.append(finalize_line(intro))
            if pains:
                pain_text = ", ".join(pains[:3])
                parts.append(finalize_line(f"It focuses on real-world challenges such as {pain_text}, breaking them down into practical decisions you can make."))
            outcome_sentence = f"By the end, you will have tangible next steps and insights you can apply immediately to {desired}."
            parts.append(finalize_line(outcome_sentence))
            combined = " ".join(parts)
            return combined

        def rewrite_or_replace_description() -> str:
            if is_invalid_description(ua_description_raw):
                return build_professional_description()
            t = ua_description_raw.strip()
            t = re.sub(r"\s+", " ", t)
            t = t.strip()
            first = t[0].upper()
            t = first + t[1:]
            if not re.search(r"[.!?]$", t):
                t += "."
            if ua_main_topic:
                if ua_main_topic.lower() not in t.lower():
                    t = f"{ua_main_topic.strip().title()}: {t}"
            if ua_desired_outcome and ua_desired_outcome.lower() not in t.lower():
                t += f" It is built to help you {ua_desired_outcome.strip()}."
            return t

        final_description = rewrite_or_replace_description()

        now_year = datetime.now().year

        # Build template variables dict
        # Helpers
        def split_sentences(text: str) -> List[str]:
            parts = re.split(r"(?<=[.!?])\s+", (text or '').strip())
            return [p.strip() for p in parts if p.strip()]
        def get_or(items: List[str], idx: int, default: str = '') -> str:
            return items[idx] if idx < len(items) and items[idx] else default
        def step(n: int) -> str:
            return f"STEP {str(n).zfill(2)}"
        def page_hdr(n: int) -> str:
            return f"PAGE {n}"

        # Quality and completion helpers
        def count_words(t: str) -> int:
            return len(re.findall(r"\b\w+\b", (t or '')))

        def ensure_min_sentences(text: str, min_sentences: int = 3, max_sentences: int = 5, topic_hint: Optional[str] = None) -> str:
            sentences = [finalize_line(s) for s in split_sentences(text)]
            # Fallback pool of professional, neutral sentences
            th = (topic_hint or 'this topic').strip()
            fallback_pool = [
                f"This section provides clear guidance on {th}.",
                "It outlines benefits, trade-offs, and common pitfalls to avoid.",
                "Recommendations and steps help readers take confident action.",
                "Examples illustrate how to apply ideas in real-world scenarios.",
            ]
            i = 0
            while len(sentences) < min_sentences and i < len(fallback_pool):
                sentences.append(finalize_line(fallback_pool[i]))
                i += 1
            # Keep it concise
            sentences = sentences[:max_sentences]
            return " ".join(sentences)

        def ensure_min_words(text: str, min_words: int = 60, max_words: int = 220, topic_hint: Optional[str] = None) -> str:
            t = (text or '').strip()
            if count_words(t) >= min_words:
                return t
            th = (topic_hint or 'the topic').strip()
            additions = [
                f"The discussion focuses on key considerations for {th}.",
                "It balances practicality with strategic outcomes and long-term value.",
                "Readers gain clarity on next steps and measurable results.",
            ]
            for line in additions:
                if count_words(t) >= min_words:
                    break
                t = (t + " " + finalize_line(line)).strip()
            words = t.split()
            if len(words) > max_words:
                t = " ".join(words[:max_words])
            return t

        def normalize_main_content(text: str, title_hint: str) -> str:
            t = re.sub(r"\s+", " ", (text or '').strip())
            t = ensure_min_sentences(t, min_sentences=3, max_sentences=5, topic_hint=title_hint)
            t = ensure_min_words(t, min_words=60, max_words=220, topic_hint=title_hint)
            return t

        def _clamp_channel(x: float) -> int:
            return max(0, min(255, int(round(x))))

        def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
            c = (color or "").strip()
            if not c:
                return (0, 0, 0)
            if c.startswith("#"):
                c = c[1:]
            if len(c) == 3:
                c = "".join(ch * 2 for ch in c)
            if len(c) != 6:
                return (0, 0, 0)
            try:
                r = int(c[0:2], 16)
                g = int(c[2:4], 16)
                b = int(c[4:6], 16)
                return (r, g, b)
            except ValueError:
                return (0, 0, 0)

        def _rgb_to_hex(r: int, g: int, b: int) -> str:
            return "#{:02x}{:02x}{:02x}".format(_clamp_channel(r), _clamp_channel(g), _clamp_channel(b))

        def _mix_rgb(
            base: Tuple[int, int, int],
            other: Tuple[int, int, int],
            base_percent: float,
        ) -> Tuple[int, int, int]:
            ratio = max(0.0, min(1.0, base_percent))
            br, bg, bb = base
            or_, og, ob = other
            r = br * ratio + or_ * (1.0 - ratio)
            g = bg * ratio + og * (1.0 - ratio)
            b = bb * ratio + ob * (1.0 - ratio)
            return (
                _clamp_channel(r),
                _clamp_channel(g),
                _clamp_channel(b),
            )

        def _derive_palette(primary_hex: str, secondary_hex: str) -> Dict[str, str]:
            white = (255, 255, 255)
            black = (0, 0, 0)
            primary = _hex_to_rgb(primary_hex or "#000000")
            secondary = _hex_to_rgb(secondary_hex or "#000000")

            palette = {}
            palette["primary10"] = _rgb_to_hex(*_mix_rgb(primary, white, 0.10))
            palette["primary20"] = _rgb_to_hex(*_mix_rgb(primary, white, 0.20))
            palette["primary40"] = _rgb_to_hex(*_mix_rgb(primary, white, 0.40))
            palette["primary80"] = _rgb_to_hex(*_mix_rgb(primary, black, 0.80))

            palette["secondary10"] = _rgb_to_hex(*_mix_rgb(secondary, white, 0.10))
            palette["secondary20"] = _rgb_to_hex(*_mix_rgb(secondary, white, 0.20))
            palette["secondary60"] = _rgb_to_hex(*_mix_rgb(secondary, white, 0.60))
            palette["secondaryDark"] = _rgb_to_hex(*_mix_rgb(secondary, black, 0.80))

            rule_rgb = _mix_rgb(primary, white, 0.18)
            palette["ruleColor"] = _rgb_to_hex(*rule_rgb)

            text_rgb = _mix_rgb(primary, black, 0.85)
            palette["textColor"] = _rgb_to_hex(*text_rgb)

            muted_rgb = _mix_rgb(primary, white, 0.48)
            palette["mutedColor"] = _rgb_to_hex(*muted_rgb)

            return palette

        def split_headline_lines(title: str) -> List[str]:
            words = re.findall(r"\S+", (title or ""))
            if not words:
                return ["", "", ""]
            if len(words) <= 4:
                return [" ".join(words), "", ""]
            if len(words) <= 8:
                return [" ".join(words[:4]), " ".join(words[4:]), ""]
            return [" ".join(words[:4]), " ".join(words[4:8]), " ".join(words[8:])]

        raw_title = (cover.get("title") or "Professional Guide").strip()

        def clean_title(title: str) -> str:
            t = (title or "").strip()
            # Remove common prefixes like "Custom Guide:" or "Guide:"
            t = re.sub(r"^(custom\s+guide\s*:|guide\s*:)", "", t, flags=re.IGNORECASE).strip()

            # Remove explicit trailing "for/by <company_name>" if present
            if company_name:
                cn = company_name.strip()
                if cn:
                    t = re.sub(rf"\s+(for|by)\s+{re.escape(cn)}\b[ .\-]*$", "", t, flags=re.IGNORECASE)

            # Remove generic trailing marketing suffix: "for/by <Proper Noun phrase>"
            # Matches one or more capitalized words at the end
            t = re.sub(r"\s+(for|by)\s+[A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*)*[ .\-]*$", "", t, flags=re.IGNORECASE)

            # Remove trailing prepositions
            t = re.sub(r'\s+(of|in|for)$', '', t, flags=re.IGNORECASE).strip()

            # Remove trailing colon and dangling single-letter articles
            t = re.sub(r"[:\s]+$", "", t).strip()
            t = re.sub(r"[:\-\s]+(A|An|The)$", "", t, flags=re.IGNORECASE).strip()

            # Collapse multiple spaces and trim punctuation
            t = re.sub(r"\s+", " ", t)
            t = t.strip(" -:;.,")
            # Keep it concise
            return truncate_title(t) if 'truncate_title' in locals() else t[:60]

        main_title = clean_title(raw_title)
        enhanced_title = main_title
        
        palette = _derive_palette(primary_color, secondary_color)

        template_vars = {
            "documentTitle": enhanced_title.upper(),
            "mainTitle": enhanced_title,
            "documentSubtitle": sloganize(cover.get("subtitle", "")),
            "companyName": company_name,
            "companySubtitle": company_subtitle,
            "primaryColor": primary_color,
            "secondaryColor": secondary_color,
            "accentColor": accent_color,
            "logoUrl": logo_url,
            "leadMagnetDescription": truncate_content(final_description),
            "phoneNumber": phone,
            "emailAddress": email,
            "website": website,
            "headerText1": step(1),
            "headerText2": step(2),
            "headerText3": step(3),
            "headerText4": step(4),
            "headerText5": step(5),
            "headerText6": step(6),
            "headerText7": step(7),
            "headerText8": step(8),
            "sectionTitle1": "Terms of Use",
            "sectionTitle2": "Contents",
            "sectionTitle3": truncate_title(clean_title(get_section(0).get("title", ""))),
            "sectionTitle4": truncate_title(clean_title(get_section(1).get("title", ""))),
            "sectionTitle5": truncate_title(clean_title(get_section(2).get("title", ""))),
            "sectionTitle6": truncate_title(clean_title(get_section(3).get("title", ""))),
            "sectionTitle7": truncate_title(clean_title(get_section(4).get("title", ""))),
            "sectionTitle8": "Next Step",
            "pageNumberHeader2": page_hdr(2),
            "pageNumberHeader3": page_hdr(3),
            "pageNumberHeader4": page_hdr(4),
            "pageNumberHeader5": page_hdr(5),
            "pageNumberHeader6": page_hdr(6),
            "pageNumberHeader7": page_hdr(7),
            "pageNumberHeader8": page_hdr(8),
            "pageNumberHeader9": page_hdr(9),

            "pageNumber2": 2,
            "pageNumber3": 3,
            "pageNumber4": 4,
            "pageNumber5": 5,
            "pageNumber6": 6,
            "pageNumber7": 7,
            "pageNumber8": 8,
            "pageNumber9": 9,
            "contentsTitle": contents.get("title", "Contents"),
            "contentItem1": truncate_title(clean_title(get_or(content_items, 0, get_section(0).get("title", "")))),
            "contentItem2": truncate_title(clean_title(get_or(content_items, 1, get_section(1).get("title", "")))),
            "contentItem3": truncate_title(clean_title(get_or(content_items, 2, get_section(2).get("title", "")))),
            "contentItem4": truncate_title(clean_title(get_or(content_items, 3, get_section(3).get("title", "")))),
            "contentItem5": truncate_title(clean_title(get_or(content_items, 4, get_section(4).get("title", "")))),
            "contentItem6": truncate_title(clean_title(get_or(content_items, 5, contact.get("title", "Contact & Next Steps")))),
            "termsTitle": terms_title,
            "termsSummary": truncate_content(terms_summary),
            "termsParagraph1": truncate_content(get_or(terms_paragraphs, 0, "")),
            "termsParagraph2": truncate_content(get_or(terms_paragraphs, 1, "")),
            "termsParagraph3": truncate_content(get_or(terms_paragraphs, 2, "")),
            "termsParagraph4": truncate_content(get_or(terms_paragraphs, 3, "")),
            "termsParagraph5": truncate_content(get_or(terms_paragraphs, 4, "")),
            "footerText": f"© {now_year} {company_name}. All rights reserved.",
            "customTitle1": truncate_title(clean_title(get_section(0).get("title", ""))),
            "customContent1": truncate_content(standardize_sustainable_terms(normalize_main_content(get_section(0).get("content", ""), get_section(0).get("title", "Section 1")))),
            "subheading1": truncate_title(get_sub(0, 0).get("title", "")),
            "subcontent1": truncate_subcontent(get_sub(0, 0).get("content", "")),
            "boxTitle1": truncate_title(get_sub(0, 1).get("title", "")),
            "boxContent1": truncate_subcontent(get_sub(0, 1).get("content", "")),
            "accentBoxTitle1": truncate_title(get_sub(0, 0).get("title", "")),
            "accentBoxContent1": truncate_subcontent(get_sub(0, 0).get("content", "")),
            "customTitle2": truncate_title(clean_title(get_section(1).get("title", ""))),
            "customContent2": truncate_content(standardize_sustainable_terms(normalize_main_content(get_section(1).get("content", ""), get_section(1).get("title", "Section 2")))),
            "subheading2": truncate_title(get_sub(1, 0).get("title", "")),
            "subcontent2": truncate_subcontent(get_sub(1, 0).get("content", "")),
            "listItem1": finalize_line(truncate_text(get_or(split_sentences(get_section(1).get("content", "")), 0, ""), 90)),
            "listItem2": finalize_line(truncate_text(get_or(split_sentences(get_section(1).get("content", "")), 1, ""), 90)),
            "listItem3": finalize_line(truncate_text(get_or(split_sentences(get_section(1).get("content", "")), 2, ""), 90)),
            "listItem4": finalize_line(truncate_text(get_or(split_sentences(get_section(1).get("content", "")), 3, ""), 90)),
            "quoteText1": truncate_subcontent(split_sentences(get_section(1).get("content", ""))[0] if split_sentences(get_section(1).get("content", "")) else ""),
            "quoteAuthor1": company_name or "",
            "customTitle3": truncate_title(clean_title(get_section(2).get("title", ""))),
            "customContent3": truncate_content(standardize_sustainable_terms(normalize_main_content(get_section(2).get("content", ""), get_section(2).get("title", "Section 3")))),
            "accentBoxTitle2": truncate_title(get_sub(2, 0).get("title", "")),
            "accentBoxContent2": truncate_subcontent(get_sub(2, 0).get("content", "")),
            "subheading3": truncate_title(get_sub(2, 1).get("title", "")),
            "subcontent3": truncate_subcontent(get_sub(2, 1).get("content", "")),
            "boxTitle2": truncate_title(get_sub(2, 0).get("title", "")),
            "boxContent2": truncate_subcontent(get_sub(2, 0).get("content", "")),
            "customTitle4": truncate_title(clean_title(get_section(3).get("title", ""))),
            "customContent4": truncate_content(standardize_sustainable_terms(normalize_main_content(get_section(3).get("content", ""), get_section(3).get("title", "Section 4")))),
            "columnBoxTitle1": truncate_title(get_sub(3, 0).get("title", "")),
            "columnBoxContent1": truncate_subcontent(get_sub(3, 0).get("content", "")),
            "columnTitle2": truncate_title(get_sub(3, 1).get("title", "")),
            "columnContent2": truncate_subcontent(get_sub(3, 1).get("content", "")),
            "boxTitle3": truncate_title(get_section(3).get("title", "")),
            "boxContent3": truncate_subcontent(get_sub(3, 0).get("content", "")),
            "subheading4": truncate_title(get_sub(3, 1).get("title", "")),
            "subcontent4": truncate_subcontent(get_sub(3, 1).get("content", "")),
            "customTitle5": truncate_title(clean_title(get_section(4).get("title", ""))),
            "customContent5": truncate_content(standardize_sustainable_terms(normalize_main_content(get_section(4).get("content", ""), get_section(4).get("title", "Section 5")))),
            "accentBoxTitle3": truncate_title(get_sub(4, 0).get("title", "")),
            "accentBoxContent3": truncate_subcontent(get_sub(4, 0).get("content", "")),
            "subheading5": truncate_title(get_sub(4, 1).get("title", "")),
            "numberedItem1": finalize_line(truncate_text(get_or(split_sentences(get_section(4).get("content", "")), 0, ""), 90)),
            "numberedItem2": finalize_line(truncate_text(get_or(split_sentences(get_section(4).get("content", "")), 1, ""), 90)),
            "numberedItem3": finalize_line(truncate_text(get_or(split_sentences(get_section(4).get("content", "")), 2, ""), 90)),
            "numberedItem4": finalize_line(truncate_text(get_or(split_sentences(get_section(4).get("content", "")), 3, ""), 90)),
            "quoteText2": truncate_subcontent(split_sentences(get_section(4).get("content", ""))[0] if split_sentences(get_section(4).get("content", "")) else ""),
            "quoteAuthor2": company_name or "",
            "contactTitle": contact.get("title", "") or "Next Step",
            "contactDescription": "",
            "differentiatorTitle": "",
            "differentiator": "",
            "ctaText": "",
            "qualityWarnings": "",
            "qualityHasWarnings": False,
        }

        template_vars["customTitle6"] = truncate_title(clean_title(get_section(5).get("title", "")))
        template_vars["customContent6"] = truncate_content(
            standardize_sustainable_terms(
                normalize_main_content(
                    get_section(5).get("content", ""),
                    get_section(5).get("title", "Section 6"),
                )
            )
        )
        template_vars["customTitle7"] = truncate_title(clean_title(get_section(6).get("title", "")))
        template_vars["customContent7"] = truncate_content(
            standardize_sustainable_terms(
                normalize_main_content(
                    get_section(6).get("content", ""),
                    get_section(6).get("title", "Section 7"),
                )
            )
        )
        template_vars["customTitle8"] = truncate_title(clean_title(get_section(7).get("title", "")))
        template_vars["customContent8"] = truncate_content(
            standardize_sustainable_terms(
                normalize_main_content(
                    get_section(7).get("content", ""),
                    get_section(7).get("title", "Section 8"),
                )
            )
        )
        template_vars["customTitle9"] = truncate_title(clean_title(get_section(8).get("title", "")))
        template_vars["customContent9"] = truncate_content(
            standardize_sustainable_terms(
                normalize_main_content(
                    get_section(8).get("content", ""),
                    get_section(8).get("title", "Section 9"),
                )
            )
        )
        template_vars["customTitle10"] = truncate_title(clean_title(get_section(9).get("title", "")))
        template_vars["customContent10"] = truncate_content(
            standardize_sustainable_terms(
                normalize_main_content(
                    get_section(9).get("content", ""),
                    get_section(9).get("title", "Section 10"),
                )
            )
        )

        sec1_sentences = split_sentences(template_vars["customContent1"])
        if len(sec1_sentences) > 2:
            template_vars["customContent1b"] = truncate_content(" ".join(sec1_sentences[2:]))
        else:
            template_vars["customContent1b"] = ""

        sec8_sentences = split_sentences(template_vars["customContent8"])
        if len(sec8_sentences) > 2:
            template_vars["customContent8b"] = truncate_content(" ".join(sec8_sentences[2:]))
        else:
            template_vars["customContent8b"] = ""

        sec10_sentences = split_sentences(template_vars["customContent10"])
        if len(sec10_sentences) > 2:
            template_vars["customContent10b"] = truncate_content(" ".join(sec10_sentences[2:]))
        else:
            template_vars["customContent10b"] = ""

        captions1 = split_sentences(get_section(0).get("content", ""))
        captions2 = split_sentences(get_section(1).get("content", ""))
        captions3 = split_sentences(get_section(2).get("content", ""))
        template_vars["imageCaption1"] = truncate_subcontent(get_or(captions1, 0, ""))
        template_vars["imageCaption2"] = truncate_subcontent(get_or(captions2, 0, ""))
        template_vars["imageCaption3"] = truncate_subcontent(get_or(captions3, 0, ""))

        template_vars["primary10Color"] = palette["primary10"]
        template_vars["primary20Color"] = palette["primary20"]
        template_vars["primary40Color"] = palette["primary40"]
        template_vars["primary80Color"] = palette["primary80"]
        template_vars["secondary10Color"] = palette["secondary10"]
        template_vars["secondary20Color"] = palette["secondary20"]
        template_vars["secondary60Color"] = palette["secondary60"]
        template_vars["secondaryDarkColor"] = palette["secondaryDark"]
        template_vars["ruleColor"] = palette["ruleColor"]
        template_vars["textColor"] = palette["textColor"]
        template_vars["mutedColor"] = palette["mutedColor"]

        template_vars["primaryMidColor"] = primary_color
        template_vars["creamColor"] = cream_color
        template_vars["creamDarkColor"] = cream_dark_color
        template_vars["inkColor"] = ink_color
        template_vars["inkMidColor"] = ink_mid_color
        template_vars["inkLightColor"] = ink_light_color
        template_vars["ruleColor"] = rule_color

        headline_lines = split_headline_lines(enhanced_title)
        aud_phrase_for_cover = audience_phrase(ua_target_audience)
        series_label_base = ua_main_topic or enhanced_title or company_name or "Insights"
        template_vars["coverSeriesLabel"] = series_label_base.upper()
        eyebrow_source = aud_phrase_for_cover or ua_industry or "Insight Report"
        template_vars["coverEyebrow"] = eyebrow_source.upper()
        template_vars["coverHeadlineLine1"] = headline_lines[0]
        template_vars["coverHeadlineLine2"] = headline_lines[1] or headline_lines[0]
        template_vars["coverHeadlineLine3"] = headline_lines[2]
        template_vars["coverTagline"] = company_subtitle or f"{now_year} Edition"

        template_vars["termsHeadlineLine1"] = truncate_title(terms_title)
        if terms_summary:
            template_vars["termsHeadlineLine2"] = truncate_title(terms_summary)
        else:
            template_vars["termsHeadlineLine2"] = "How to use this guide"
        pull_source = terms_summary or get_or(terms_paragraphs, 0, "")
        pull_sentences = split_sentences(pull_source)
        template_vars["termsPullQuote"] = truncate_subcontent(pull_sentences[0] if pull_sentences else "")

        template_vars["tocHeadlineLine1"] = enhanced_title
        template_vars["tocHeadlineLine2"] = ua_main_topic.title() if ua_main_topic else company_name or ""
        template_vars["tocSubtitle"] = truncate_content(final_description)
        template_vars["contentItem1Sub"] = truncate_title(template_vars.get("subheading1", ""))
        template_vars["contentItem2Sub"] = truncate_title(template_vars.get("subheading2", ""))
        template_vars["contentItem3Sub"] = truncate_title(template_vars.get("subheading3", ""))
        template_vars["contentItem4Sub"] = truncate_title(template_vars.get("subheading4", ""))
        template_vars["contentItem5Sub"] = truncate_title(template_vars.get("subheading5", ""))
        template_vars["contentItem6Sub"] = "Next steps and action plan"

        template_vars["sectionLabel3"] = template_vars.get("sectionTitle3", "")
        template_vars["sectionLabel4"] = template_vars.get("sectionTitle4", "")
        template_vars["sectionLabel5"] = template_vars.get("sectionTitle5", "")
        template_vars["sectionLabel6"] = template_vars.get("sectionTitle6", "")
        template_vars["sectionLabel7"] = template_vars.get("sectionTitle7", "")
        template_vars["sectionLabel8"] = template_vars.get("sectionTitle8", "")

        template_vars["chapterLabel1"] = "CHAPTER 01"
        template_vars["chapterLabel2"] = "CHAPTER 02"
        template_vars["chapterLabel3"] = "CHAPTER 03"
        template_vars["chapterLabel4"] = "CHAPTER 04"
        template_vars["chapterLabel5"] = "CHAPTER 05"
        template_vars["chapterLabel6"] = "CHAPTER 06"
        template_vars["chapterLabel7"] = "CHAPTER 07"
        template_vars["chapterLabel8"] = "CHAPTER 08"
        template_vars["chapterLabel9"] = "CHAPTER 09"
        template_vars["chapterLabel10"] = "CHAPTER 10"

        pains_for_stats = pain_points_list(ua_pain_points)
        sections_count = len(sections) if sections else 5
        pain_count = len(pains_for_stats) if pains_for_stats else 3
        template_vars["stat1Value"] = str(sections_count)
        template_vars["stat1Label"] = "Sections in this issue"
        template_vars["stat2Value"] = str(pain_count)
        template_vars["stat2Label"] = "Pain points addressed"
        template_vars["stat3Value"] = "1"
        template_vars["stat3Label"] = "Action plan at the end"

        template_vars["page4Stat1Value"] = str(sections_count)
        template_vars["page4Stat1Desc"] = "Core sections you will explore"
        template_vars["page4Stat2Value"] = str(pain_count)
        template_vars["page4Stat2Unit"] = ""
        template_vars["page4Stat2Desc"] = "Pain points reframed as opportunities"
        template_vars["page4Stat3Value"] = "1"
        template_vars["page4Stat3Unit"] = "PLAYBOOK"
        template_vars["page4Stat3Desc"] = "Structured next steps at the end"

        template_vars["page6Stat1Value"] = "100"
        template_vars["page6Stat1Desc"] = "Focused on practical decisions"
        template_vars["page6Stat2Value"] = str(now_year)
        template_vars["page6Stat2Desc"] = "Edition year"
        template_vars["page6Stat3Value"] = "3"
        template_vars["page6Stat3Unit"] = "+"
        template_vars["page6Stat3Desc"] = "Ways to move forward"

        template_vars["page9Stat1Value"] = template_vars.get("page4Stat1Value", template_vars.get("stat1Value", "3"))
        template_vars["page9Stat1Desc"] = "Key ideas in this chapter"
        template_vars["page9Stat2Value"] = template_vars.get("page4Stat2Value", template_vars.get("stat2Value", "3"))
        template_vars["page9Stat2Unit"] = template_vars.get("page4Stat2Unit", "")
        template_vars["page9Stat2Desc"] = "Pain points reframed here"
        template_vars["page9Stat3Value"] = template_vars.get("page4Stat3Value", "1")
        template_vars["page9Stat3Unit"] = template_vars.get("page4Stat3Unit", "PLAYBOOK")
        template_vars["page9Stat3Desc"] = "Action framework on these pages"

        if not template_vars.get("quoteText1"):
            sec2_sentences = split_sentences(get_section(1).get("content", ""))
            template_vars["quoteText1"] = truncate_subcontent(sec2_sentences[0] if sec2_sentences else "")
        template_vars["pullQuote1"] = template_vars.get("quoteText1", "")

        template_vars["calloutLabel1"] = template_vars.get("accentBoxTitle1", "") or "Key insight"
        template_vars["calloutContent1"] = template_vars.get("accentBoxContent1", "")
        template_vars["calloutLabel2"] = template_vars.get("accentBoxTitle2", "") or "In practice"
        template_vars["calloutContent2"] = template_vars.get("accentBoxContent2", "")
        template_vars["calloutLabel3"] = "Quick win"
        template_vars["calloutContent3"] = truncate_subcontent(get_or(split_sentences(get_section(5).get("content", "")), 0, ""))
        template_vars["calloutLabel4"] = "Next step"
        template_vars["calloutContent4"] = truncate_subcontent(get_or(split_sentences(get_section(7).get("content", "")), 0, ""))

        template_vars["infoBoxLabel1"] = template_vars.get("accentBoxTitle2", "") or "Design note"
        template_vars["infoBoxContent1"] = template_vars.get("accentBoxContent2", "")
        template_vars["infoBoxLabel2"] = template_vars.get("accentBoxTitle3", "") or "Implementation tip"
        template_vars["infoBoxContent2"] = template_vars.get("accentBoxContent3", "")
        template_vars["infoBoxLabel3"] = template_vars.get("boxTitle3", "") or template_vars.get("customTitle4", "")
        template_vars["infoBoxContent3"] = template_vars.get("boxContent3", "")
        template_vars["infoBoxLabel4"] = "What this means in practice"
        template_vars["infoBoxContent4"] = truncate_subcontent(get_or(split_sentences(get_section(5).get("content", "")), 1, ""))
        template_vars["infoBoxLabel5"] = "Watch for"
        template_vars["infoBoxContent5"] = truncate_subcontent(get_or(split_sentences(get_section(6).get("content", "")), 0, ""))
        template_vars["infoBoxLabel6"] = "When to use this"
        template_vars["infoBoxContent6"] = truncate_subcontent(get_or(split_sentences(get_section(7).get("content", "")), 1, ""))
        template_vars["infoBoxLabel7"] = "If you remember one thing"
        template_vars["infoBoxContent7"] = truncate_subcontent(get_or(split_sentences(get_section(8).get("content", "")), 0, ""))

        template_vars["colCard1Title"] = template_vars.get("columnBoxTitle1", "") or "Scenario 1"
        template_vars["colCard1Content"] = template_vars.get("columnBoxContent1", "")
        template_vars["colCard2Title"] = template_vars.get("columnTitle2", "") or "Scenario 2"
        template_vars["colCard2Content"] = template_vars.get("columnContent2", "")

        template_vars["imageLabel1"] = truncate_title(get_section(0).get("title", "") or template_vars.get("contentItem1", "Overview"))
        template_vars["imageLabel2"] = truncate_title(get_section(1).get("title", "") or template_vars.get("contentItem2", "Details"))
        template_vars["imageLabel3"] = truncate_title(get_section(2).get("title", "") or template_vars.get("contentItem3", "Strategy"))
        template_vars["imageLabel4a"] = truncate_title(template_vars.get("subheading4", "") or template_vars.get("contentItem4", "Design Focus"))
        template_vars["imageLabel4b"] = truncate_title(template_vars.get("columnTitle2", "") or template_vars.get("contentItem4", "Implementation"))
        template_vars["imageLabel5"] = truncate_title(get_section(4).get("title", "") or template_vars.get("contentItem5", "Checklist"))
        template_vars["imageLabel6"] = truncate_title(get_section(5).get("title", "") or template_vars.get("contentItem5", "Scenario"))
        template_vars["imageLabel7"] = truncate_title(get_section(6).get("title", "") or template_vars.get("contentItem5", "Playbook"))
        template_vars["imageLabel8"] = truncate_title(get_section(7).get("title", "") or template_vars.get("contentItem6", "Action"))

        final_cta = render_final_cta()
        template_vars["sectionTitle8"] = final_cta.get("section_title", template_vars.get("sectionTitle8", "Next Step"))
        template_vars["contactDescription"] = truncate_content(final_cta.get("description", ""))
        template_vars["differentiatorTitle"] = final_cta.get("offer_name", "") or template_vars.get("differentiatorTitle", "")
        template_vars["differentiator"] = finalize_line(truncate_text(final_cta.get("differentiator", ""), 180))
        template_vars["ctaText"] = finalize_line(truncate_text(final_cta.get("action_text", ""), 180))

        template_vars["ctaHeadlineLine1"] = template_vars.get("sectionTitle8", "Next Step")
        template_vars["ctaHeadlineLine2"] = final_cta.get("offer_name", "")
        template_vars["ctaEyebrow"] = "Action Plan"
        template_vars["ctaTitle"] = final_cta.get("offer_name", "") or template_vars.get("contactTitle", "")

        template_vars["contactLabel1"] = "Email"
        template_vars["contactValue1"] = email or template_vars.get("emailAddress", "")
        template_vars["contactLabel2"] = "Website"
        template_vars["contactValue2"] = website or template_vars.get("website", "")
        template_vars["contactLabel3"] = "Phone"
        template_vars["contactValue3"] = phone or template_vars.get("phoneNumber", "")

        # Build basic quality warnings for client-side display
        warnings: List[str] = []
        # Incomplete titles (dangling punctuation or single-letter endings)
        title_samples = [
            template_vars["sectionTitle1"],
            template_vars["sectionTitle2"],
            template_vars["sectionTitle3"],
            template_vars["sectionTitle4"],
            template_vars["sectionTitle5"],
        ]
        if any(re.search(r"[:\-]\s*$", t) or re.search(r"\b(A|An|The)$", t, flags=re.IGNORECASE) for t in title_samples if t):
            warnings.append("Some section titles appear incomplete (e.g., trailing colon/article).")

        # Content completeness: ensure minimum sentences/words
        content_samples = [
            template_vars["customContent1"],
            template_vars["customContent2"],
            template_vars["customContent3"],
            template_vars["customContent4"],
            template_vars["customContent5"],
        ]
        if any(len(split_sentences(c)) < 3 or count_words(c) < 60 for c in content_samples if c):
            warnings.append("Some sections may be too brief; expanded to improve coherence.")

        # Tone checks: excessive exclamation or ALL CAPS streaks
        if any(c.count("!") > 1 or re.search(r"\b[A-Z]{6,}\b", c) for c in content_samples if c):
            warnings.append("Detected informal tone or emphasis; adjusted toward professional style.")

        if warnings:
            template_vars["qualityWarnings"] = " • ".join(warnings)
            template_vars["qualityHasWarnings"] = True

        # Debug mapping summary
        print("🔎 MAP VARS: colors", {"primary": primary_color, "secondary": secondary_color, "accent": accent_color})
        print("🔎 MAP VARS: firm", {"name": company_name, "email": email, "phone": phone, "website": website, "logo": bool(logo_url)})
        print("🔎 MAP VARS: counts", {"sections": len(sections), "contentItems": len(content_items), "termsParas": len(terms_paragraphs)})
        print("🔎 MAP VARS: enhanced_title", enhanced_title)

        return template_vars

    def _create_slogan_prompt(self, user_answers: Dict[str, Any], firm_profile: Dict[str, Any]) -> str:
        return f"""
        Generate a short, catchy slogan for an architecture firm.
        Firm Name: {firm_profile.get('firm_name', 'An Architecture Firm')}
        Specialization: {user_answers.get('lead_magnet_type', 'General Architecture')}
        Target Audience: {user_answers.get('target_audience', 'General Clients')}
        Pain Points: {user_answers.get('pain_points', 'Finding good design')}
        Desired Outcome: {user_answers.get('desired_outcome', 'A beautiful, functional space')}
        
        Based on the above, create a slogan that is less than 10 words.
        """

    def generate_slogan(self, user_answers: Dict[str, Any], firm_profile: Dict[str, Any]) -> str:
        """Generates a slogan using Perplexity AI."""
        prompt = self._create_slogan_prompt(user_answers, firm_profile)
        
        try:
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3-sonar-large-32k-online",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 30,
                },
                timeout=15
            )
            response.raise_for_status()
            slogan = response.json()['choices'][0]['message']['content'].strip()
            return slogan
        except requests.exceptions.Timeout as e:
            print(f"❌ Error calling Perplexity API for slogan: {e}")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"❌ Error calling Perplexity API for slogan: {e}")
            return ""

    def check_available_models(self):
        """Debug method to check what models are available with your API key"""
        if not self.api_key:
            print("❌ PERPLEXITY_API_KEY not configured")
            return
            
        try:
            response = requests.get(
                "https://api.perplexity.ai/models",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            if response.status_code == 200:
                models = response.json()
                print("✅ Available Perplexity models:")
                for model in models.get('data', []):
                    print(f"  - {model['id']}")
            else:
                print(f"❌ Cannot fetch models: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Error checking models: {e}")

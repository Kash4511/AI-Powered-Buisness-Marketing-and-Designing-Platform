import os
from pathlib import Path
import json
import requests
import re
import logging
import concurrent.futures
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

logger = logging.getLogger(__name__)

class PerplexityClient:
    """Client for interacting with Perplexity AI API for lead magnet content generation"""
    
    def __init__(self):
        # 1. Load .env from both project root and Backend/
        if load_dotenv:
            # Try current Backend/ directory
            backend_env = Path(__file__).resolve().parents[1] / '.env'
            # Try project root (one level above Backend/)
            root_env = Path(__file__).resolve().parents[2] / '.env'
            
            for env_path in [backend_env, root_env]:
                if env_path.exists():
                    try:
                        load_dotenv(env_path)
                        logger.info(f"✅ Loaded .env from: {env_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load .env from {env_path}: {e}")
        
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        self.base_url = "https://api.perplexity.ai/chat/completions"
        if not self.api_key:
            logger.warning("⚠️ PERPLEXITY_API_KEY not found in environment variables or .env")
        else:
            logger.info("✅ PerplexityClient initialized with API key")
        
    def interpret_field(self, field_value: Any) -> str:
        """
        Helper to determine if a field is meaningful or should be inferred.
        Returns 'INFER_FROM_CONTEXT' or a reinterpreted professional version.
        Handles lists and multi-line strings cleanly.
        """
        if not self._is_meaningful(field_value):
            return "INFER_FROM_CONTEXT"
        
        # Clean up the value for the prompt
        if isinstance(field_value, list):
            # Join lists into a clean string
            cleaned_value = ", ".join([str(x).strip() for x in field_value if str(x).strip()])
        else:
            # Remove excessive whitespace/newlines from strings
            cleaned_value = " ".join(str(field_value).split())
            
        if not cleaned_value or len(cleaned_value) < 2:
            return "INFER_FROM_CONTEXT"

        # Return a marker that tells AI to reinterpret it.
        return f"REINTERPRET: {cleaned_value}"

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, str]:
        """
        Converts user fields into interpreted signals for the AI prompt.
        """
        signals = {}
        for key, value in user_answers.items():
            signals[key] = self.interpret_field(value)
        return signals

    def generate_lead_magnet_json(self, signals: Dict[str, str], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            logger.error("❌ PERPLEXITY_API_KEY missing")
            raise Exception("PERPLEXITY_API_KEY is not configured")

        model_to_use = "sonar"
        try:
            logger.info(f"Generating AI content with signals (25s timeout)...")
            
            # Log which fields are being inferred vs reinterpreted
            inferred = [k for k, v in signals.items() if v == "INFER_FROM_CONTEXT"]
            reinterpreted = [k for k, v in signals.items() if v.startswith("REINTERPRET")]
            logger.info(f"📊 AI Signal Mapping: Inferred: {inferred} | Reinterpreted: {reinterpreted}")

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
                                "content": "You are a professional strategist. Output ONLY valid JSON. Be concise but deep."
                            },
                            {
                                "role": "user",
                                "content": self._create_content_prompt(signals, firm_profile)
                            }
                        ],
                        "max_tokens": 1200,
                        "temperature": 0.7
                    },
                    timeout=25
                )
        except requests.exceptions.Timeout:
            logger.error("❌ Perplexity API timeout (25s)")
            raise Exception("AI content generation timed out (25s limit).")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Perplexity API request error: {e}")
            raise Exception(f"Perplexity API request error: {e}")
        except Exception as e:
            logger.error(f"❌ Error calling Perplexity API: {str(e)}")
            raise

        logger.info(f"Perplexity response status: {response.status_code}")
        if response.status_code != 200:
            logger.error(f"❌ Perplexity API error: {response.status_code} - {response.text}")
            raise Exception(f"Perplexity API error: {response.status_code} - {response.text}")

        result = response.json()
        message_content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        json_content = self._extract_json_from_markdown(message_content)
        try:
            content = json.loads(json_content)
            return content
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON from Perplexity response: {e}")
            logger.error(f"RAW CONTENT PREVIEW: {repr(message_content)}")
            raise Exception("Invalid JSON returned from Perplexity API. Raw content logged to server.")

    def _extract_json_from_markdown(self, text: str) -> str:
        """Helper to extract JSON from markdown code blocks if present."""
        if not text: return ""
        
        # 1. Look for markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            text = json_match.group(1).strip()
        
        # 2. Look for the first { and the last }
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
            return text.strip()

        json_str = text[first_brace:last_brace+1].strip()
        
        # 3. Aggressive Truncation Repair
        # If the JSON ends abruptly (e.g. inside a string or list), try to close it.
        # This is a common issue with Perplexity timeouts or token limits.
        try:
            # Check if it's already valid
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            # Try to fix truncated JSON by removing trailing comma and closing braces
            # Pattern: matches a trailing comma followed by whitespace/newlines at the end
            json_str = re.sub(r',\s*$', '', json_str)
            
            # Count open/close markers
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')
            
            # Close missing structures
            if open_brackets > close_brackets:
                json_str += ']' * (open_brackets - close_brackets)
            if open_braces > close_braces:
                json_str += '}' * (open_braces - close_braces)
                
            return json_str


    def _is_meaningful(self, value: Any) -> bool:
        """
        Strict check for meaningful user input.
        Returns True if the input has real semantic weight.
        """
        if value is None:
            return False
            
        # Handle lists: at least one meaningful item
        if isinstance(value, list):
            return any(self._is_meaningful(item) for item in value)
            
        v = str(value).strip()
        if not v:
            return False
        
        # Rule: string length >= 2 (allow short words like 'AI', 'ROI')
        if len(v) < 2:
            return False
            
        # Common placeholder/filler check
        lowered = v.lower()
        fillers = {
            "test", "testing", "none", "n/a", "na", "null", "empty", "ok", "yes", "no", 
            "placeholder", "asdf", "qwerty", "lorem", "ipsum", "...", "h", "ok.", ".", "-"
        }
        if lowered in fillers:
            return False

        # Rule: Not just punctuation
        if not re.search(r'[A-Za-z0-9]', v):
            return False

        # Rule: Not repetitive characters (e.g. "aaaa")
        if len(v) > 4 and len(set(lowered)) <= 2:
            return False
            
        return True

    def _create_content_prompt(self, signals: Dict[str, str], firm_profile: Dict[str, Any]) -> str:
        """
        Builds a prompt from interpreted signals. 
        Never inserts raw user text directly.
        """
        prompt = f"""
        You are a senior expert content strategist. Your task is to generate a high-value, professional Lead Magnet.
        
        STRICT BEHAVIOR RULES:
        1. SEMANTIC REINTERPRETATION: You will receive 'signals' for various fields.
           - If a signal is 'INFER_FROM_CONTEXT', you must synthesize that content based on the Topic and Audience.
           - If a signal is 'REINTERPRET: [text]', you must take the user's intent, professionalize it, expand it into a full sentence, and elevate the language. Never copy verbatim.
        2. NO RAW USER TEXT: Never leak raw user inputs into the final output. Every word must be your professional generation.
        3. NO PLACEHOLDERS: Generate expert-level insights.
        4. STABLE JSON: Return valid JSON ONLY.
        
        SIGNALS:
        - Lead Magnet Type: {signals.get('lead_magnet_type', 'Expert Report')}
        - Main Topic: {signals.get('main_topic', 'Professional Strategy')}
        - Target Audience: {signals.get('target_audience', 'Industry Leaders')}
        - Audience Pain Points: {signals.get('audience_pain_points', 'Efficiency and Growth')}
        - Desired Outcome: {signals.get('desired_outcome', 'INFER_FROM_CONTEXT')}
        - Call to Action: {signals.get('call_to_action', 'INFER_FROM_CONTEXT')}
        - Firm Context: {firm_profile.get('firm_name', 'Expert Firm')} (Industry: Architecture/Design)
        
        REQUIRED OUTPUT SCHEMA:
        {{
            "title": "A compelling, professional title",
            "summary": "An executive summary that sets the stage",
            "sections": [
                {{
                    "title": "Section Title",
                    "content": "A substantial, professional explanation (120–250 words minimum). Provide deep insight, practical strategy, and industry context. Do not use bullets as the primary format; use full paragraphs."
                }}
            ],
            "key_insights": ["Strategic Insight 1", "Strategic Insight 2", "Strategic Insight 3"],
            "outcome_statement": "A concrete, professional value proposition based on the Desired Outcome signal.",
            "call_to_action": {{
                "headline": "A high-converting headline",
                "description": "The professional reasoning for the next step",
                "button_text": "Action-oriented verb"
            }}
        }}
        
        IMPORTANT: Provide 3-4 deep-dive sections. Do not include nested subsections; keep sections flat.
        STRICT RULE: Every section 'content' field must be a long-form professional explanation. Never output placeholders or empty text.
        """
        return prompt.strip()
        
    def normalize_ai_output(self, ai_result: Any) -> Dict[str, Any]:
        """
        Structural safety layer: Guarantees a safe schema for the PDF renderer.
        Flattens structures, joins paragraphs, and ensures string types.
        """
        if ai_result is None:
            return {"sections": []}

        # Final structure we guarantee
        normalized = {
            "title": "",
            "summary": "",
            "outcome_statement": "",
            "key_insights": [],
            "sections": [],
            "call_to_action": {
                "headline": "",
                "description": "",
                "button_text": ""
            }
        }

        def clean_text(text: Any) -> str:
            """Remove markdown and join lists/dicts into safe strings."""
            if text is None:
                return ""
            if isinstance(text, list):
                text = " ".join([clean_text(i) for i in text if i])
            elif isinstance(text, dict):
                # Stringify objects safely
                text = " ".join([f"{k}: {clean_text(v)}" for k, v in text.items()])
            
            s = str(text).strip()
            # Remove markdown patterns: ###, **, [links], and Markdown Tables
            s = re.sub(r'#+\s*', '', s)
            s = re.sub(r'\*+', '', s)
            s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s) # Strip links but keep text
            # Remove markdown tables: look for lines starting with | and containing |
            s = re.sub(r'\n?\|.*\|(\n\|.*\|)*', '', s)
            # Remove table separators like |---|---|
            s = re.sub(r'\|[\s-]*\|[\s\-|]*', '', s)
            return s

        def extract_sections_recursively(data: Any) -> List[Dict[str, str]]:
            """Flatten any structure into a list of {title, content}."""
            sections = []
            if isinstance(data, list):
                for item in data:
                    sections.extend(extract_sections_recursively(item))
            elif isinstance(data, dict):
                # If it looks like a section already
                if "title" in data or "content" in data:
                    sections.append({
                        "title": clean_text(data.get("title", "")),
                        "content": clean_text(data.get("content", ""))
                    })
                    # Also check for nested subsections in this dict
                    if "subsections" in data and isinstance(data["subsections"], list):
                        for sub in data["subsections"]:
                            sections.append({
                                "title": clean_text(sub.get("title", "")),
                                "content": clean_text(sub.get("content", ""))
                            })
                else:
                    # Otherwise, just extract all values as content
                    for k, v in data.items():
                        if k in ["sections", "contents", "items"]:
                            sections.extend(extract_sections_recursively(v))
                        elif isinstance(v, (str, list, dict)):
                            sections.append({
                                "title": clean_text(k),
                                "content": clean_text(v)
                            })
            return sections

        if isinstance(ai_result, dict):
            normalized["title"] = clean_text(ai_result.get("title", ""))
            normalized["summary"] = clean_text(ai_result.get("summary", ""))
            normalized["outcome_statement"] = clean_text(ai_result.get("outcome_statement", ""))
            
            # Key Insights
            raw_insights = ai_result.get("key_insights", [])
            if isinstance(raw_insights, list):
                normalized["key_insights"] = [clean_text(i) for i in raw_insights if i]
            
            # Sections
            raw_sections = ai_result.get("sections") or ai_result.get("contents") or []
            normalized["sections"] = extract_sections_recursively(raw_sections)
            
            # CTA
            raw_cta = ai_result.get("call_to_action", {})
            if isinstance(raw_cta, dict):
                normalized["call_to_action"]["headline"] = clean_text(raw_cta.get("headline", ""))
                normalized["call_to_action"]["description"] = clean_text(raw_cta.get("description", ""))
                normalized["call_to_action"]["button_text"] = clean_text(raw_cta.get("button_text", ""))
        
        elif isinstance(ai_result, list):
            normalized["sections"] = extract_sections_recursively(ai_result)

        # Final check: ensure at least an empty list for sections
        if not normalized["sections"]:
            normalized["sections"] = []

        logger.info(f"✅ AI Normalization Complete: {len(normalized['sections'])} sections secured.")
        return normalized

    def _derive_colors(self, hex_color: str) -> Dict[str, str]:
        """Derives opacity variants of a hex color for the template."""
        if not hex_color or not hex_color.startswith("#") or len(hex_color) != 7:
            return {}
        
        # Simple implementation: just return rgba versions for the CSS variables
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            return {
                "10": f"rgba({r}, {g}, {b}, 0.1)",
                "20": f"rgba({r}, {g}, {b}, 0.2)",
                "40": f"rgba({r}, {g}, {b}, 0.4)",
                "60": f"rgba({r}, {g}, {b}, 0.6)",
                "80": f"rgba({r}, {g}, {b}, 0.8)",
            }
        except Exception:
            return {}

    def ensure_section_content(self, sections: List[Dict[str, str]], signals: Dict[str, str], firm_profile: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Content Guarantee Layer: Ensures no section has empty or too short content.
        Regenerates sections that fail the quality check in PARALLEL to save time.
        """
        if not sections:
            logger.warning("⚠️ ensure_section_content: No sections to check.")
            return []

        MIN_THRESHOLD = 40  # Minimum characters for meaningful content
        indices_to_regenerate = []
        
        for idx, sec in enumerate(sections):
            content = str(sec.get("content", "")).strip()
            if not content or len(content) < MIN_THRESHOLD:
                indices_to_regenerate.append(idx)
        
        if not indices_to_regenerate:
            logger.info(f"📊 Content Guarantee Complete. All {len(sections)} sections are healthy.")
            return sections

        logger.info(f"❗ Found {len(indices_to_regenerate)} empty or short sections (indices: {indices_to_regenerate}). Starting parallel regeneration...")

        # Run regenerations in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(indices_to_regenerate)) as executor:
            # Map futures to their section indices
            future_to_idx = {
                executor.submit(
                    self.regenerate_section_content, 
                    sections[idx].get("title", "Strategic Section"), 
                    signals, 
                    firm_profile
                ): idx for idx in indices_to_regenerate
            }
            
            regenerated_count = 0
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                title = sections[idx].get("title", "Strategic Section")
                try:
                    new_content = future.result()
                    if new_content and len(new_content) >= MIN_THRESHOLD:
                        sections[idx]["content"] = new_content
                        regenerated_count += 1
                        logger.info(f"✅ Section '{title}' (idx: {idx}) regenerated successfully ({len(new_content)} chars).")
                    else:
                        logger.error(f"❌ Regeneration for '{title}' (idx: {idx}) failed to produce meaningful content.")
                        raise Exception(f"Content synthesis failed for section: {title}")
                except Exception as e:
                    logger.error(f"❌ Critical failure in content guarantee for '{title}' (idx: {idx}): {str(e)}")
                    raise

        logger.info(f"📊 Content Guarantee Complete. Regenerated {regenerated_count} sections. Final count: {len(sections)}")
        return sections

    def regenerate_section_content(self, section_title: str, signals: Dict[str, str], firm_profile: Dict[str, Any]) -> str:
        """ Targeted AI call to synthesize content for a single section. """
        prompt = f"""
        You are an expert strategist generating content for a professional guide.
        
        CONTEXT:
        - Main Topic: {signals.get('main_topic', 'Professional Strategy')}
        - Target Audience: {signals.get('target_audience', 'Industry Leaders')}
        - Audience Pain Points: {signals.get('audience_pain_points', 'Efficiency and Growth')}
        - Firm Context: {firm_profile.get('firm_name', 'Expert Firm')}
        
        TASK:
        Write a deep-dive professional section for the topic: "{section_title}"
        
        REQUIREMENTS:
        - Write 120–250 words minimum.
        - Explain the topic in detail, providing practical insights and professional strategy.
        - Use full paragraphs. Do not use only bullet points.
        - Tone: Expert, authoritative, and helpful.
        - No placeholders. No conversational filler.
        - Output ONLY the text for the section content. No JSON. No titles.
        """
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "You are a professional content strategist. Output only the requested text."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                timeout=12
            )
            response.raise_for_status()
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            
            # Basic cleaning: remove any markdown title or bolding that AI might have included despite instructions
            content = re.sub(r'^#+\s*.*?\n', '', content) # Remove top level header
            content = re.sub(r'\*+', '', content) # Remove bolding
            
            return content
        except Exception as e:
            logger.error(f"Error in regenerate_section_content for '{section_title}': {str(e)}")
            return ""

    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Optional[Dict[str, Any]] = None,
        user_answers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Safely map AI generated JSON content to template variables."""
        # 0. Safety Guard: Ensure ai_content is already normalized or at least a dict
        if not isinstance(ai_content, dict):
            ai_content = {"sections": []}

        firm_profile = firm_profile or {}
        user_answers = user_answers or {}
        
        # 1. Basic Metadata with defaults
        company_name = str(firm_profile.get("firm_name") or "Expert Firm").strip()
        email = str(firm_profile.get("work_email") or "").strip()
        phone = str(firm_profile.get("phone_number") or "").strip()
        website = str(firm_profile.get("firm_website") or "").strip()
        logo_url = str(firm_profile.get("logo_url") or "").strip()
        
        # 2. Colors & Style
        primary_color = str(firm_profile.get("primary_brand_color") or "#2a5766")
        secondary_color = str(firm_profile.get("secondary_brand_color") or "#ffffff")
        accent_color = "#F4A460"
        
        p_vars = self._derive_colors(primary_color)
        s_vars = self._derive_colors(secondary_color)
        
        # 3. Content Extraction from Structured AI JSON
        sections = ai_content.get("sections", [])
        if not isinstance(sections, list): 
            sections = []
        
        # Helper for safe section access
        def get_sec(idx):
            if idx < len(sections):
                s = sections[idx]
                return s if isinstance(s, dict) else {"title": "", "content": ""}
            return {"title": "", "content": ""}

        # 4. Core Mapping
        def clean_sig(s):
            if not isinstance(s, str): return ""
            return s.replace("REINTERPRET: ", "") if s.startswith("REINTERPRET") else s

        main_topic = clean_sig(user_answers.get("main_topic")) or "Strategic Framework"
        main_title = str(ai_content.get("title") or f"{main_topic}: Executive Guide").strip()
        summary = str(ai_content.get("summary") or "A comprehensive guide to strategic excellence.").strip()
        
        # Split title for cover lines safely
        title_parts = main_title.split(":", 1)
        headline_1 = title_parts[0].strip()
        headline_2 = title_parts[1].strip() if len(title_parts) > 1 else "Professional Report"

        # Extract CTA parts
        cta_obj = ai_content.get("call_to_action", {})
        if not isinstance(cta_obj, dict): cta_obj = {}

        # Derived Page Content for the complex Template.html
        template_vars = {
            # --- Metadata ---
            "mainTitle": main_title,
            "documentTitle": main_title.upper(),
            "documentSubtitle": summary,
            "companyName": company_name,
            "primaryColor": primary_color,
            "secondaryColor": secondary_color,
            "accentColor": accent_color,
            "logoUrl": logo_url,
            "emailAddress": email,
            "phoneNumber": phone,
            "website": website,
            "leadMagnetDescription": summary,
            
            # --- Colors ---
            "primary10Color": p_vars.get("10") or primary_color,
            "primary20Color": p_vars.get("20") or primary_color,
            "primary40Color": p_vars.get("40") or primary_color,
            "primary80Color": p_vars.get("80") or primary_color,
            "secondary10Color": s_vars.get("10") or secondary_color,
            "secondary20Color": s_vars.get("20") or secondary_color,
            "secondary60Color": s_vars.get("60") or secondary_color,
            "secondaryDarkColor": s_vars.get("80") or secondary_color,
            "ruleColor": p_vars.get("20") or primary_color,
            "textColor": "#333333",
            "mutedColor": "#666666",

            # --- Page 1 (Cover) ---
            "coverSeriesLabel": "EXECUTIVE SERIES",
            "coverEyebrow": "STRATEGIC ANALYSIS",
            "coverHeadlineLine1": headline_1,
            "coverHeadlineLine2": headline_2,
            "coverHeadlineLine3": company_name,
            "coverTagline": str(ai_content.get("outcome_statement") or summary).strip(),
            "stat1Value": "100%", "stat1Label": "PROFESSIONAL",
            "stat2Value": "AI", "stat2Label": "OPTIMIZED",
            "stat3Value": datetime.now().year, "stat3Label": "EDITION",

            # --- Page 2 (Terms) ---
            "sectionTitle1": "Introduction",
            "termsHeadlineLine1": "Strategic",
            "termsHeadlineLine2": "Perspective",
            "termsParagraph1": summary,
            "termsParagraph2": "This guide provides expert insights designed to facilitate professional growth and strategic alignment.",
            "termsPullQuote": "Strategy is not about being different, but about making a difference.",
            "termsParagraph3": "Our approach combines data-driven analysis with practical implementation frameworks.",
            "termsParagraph4": "We empower organizations to navigate complexity with clarity and purpose.",

            # --- Page 3 (TOC) ---
            "sectionTitle2": "Contents",
            "tocHeadlineLine1": "Strategic",
            "tocHeadlineLine2": "Roadmap",
            "tocSubtitle": "An overview of the key insights and frameworks included in this guide.",
            "contentItem1": "Introduction", "contentItem1Sub": "Setting the stage for excellence",
            "contentItem2": "Strategic Overview", "contentItem2Sub": "The landscape of opportunity",
            "contentItem3": str(get_sec(0).get("title") or "Foundations"), "contentItem3Sub": "Core principles for success",
            "contentItem4": str(get_sec(1).get("title") or "Strategy"), "contentItem4Sub": "Driving measurable impact",
            "contentItem5": str(get_sec(2).get("title") or "Execution"), "contentItem5Sub": "Turning vision into reality",
            "contentItem6": "Best Practices", "contentItem6Sub": "Maintaining the edge",
            "contentItem7": "Next Steps", "contentItem7Sub": "Taking the lead",
            "contentItem8": "Conclusion", "contentItem8Sub": "Final reflections",
            "contentItem9": "Resources", "contentItem9Sub": "Tools for growth",
            "contentItem10": "Action Plan", "contentItem10Sub": "Your path forward",

            # --- Page 4 (Chapter 1) ---
            "sectionLabel3": "CHAPTER 01",
            "chapterLabel1": "01",
            "customTitle1": str(get_sec(0).get("title") or ""),
            "customContent1": str(get_sec(0).get("content") or ""),
            "customContent1b": "", # Extra paragraph space
            "imageLabel1": "STRATEGY HERO",
            "imageCaption1": "Mapping the path to strategic alignment.",
            "subheading1": "Core Insight",
            "subcontent1": "Achieving sustainable growth requires a balance of innovation and operational discipline.",
            "calloutLabel1": "KEY TAKEAWAY",
            "calloutContent1": "Success is measured by the clarity of your intent and the consistency of your execution.",

            # --- Page 5 (Chapter 2) ---
            "sectionLabel4": "CHAPTER 02",
            "chapterLabel2": "02",
            "customTitle2": str(get_sec(1).get("title") or ""),
            "customContent2": str(get_sec(1).get("content") or ""),
            "pullQuote1": str((ai_content.get("key_insights") or ["Focus on what matters most to drive results."])[0]),
            "subheading2": "Analysis",
            "subcontent2": "Deep-dive analysis reveals the hidden opportunities within your current framework.",
            "listItem1": "Identify core value drivers",
            "listItem2": "Optimize resource allocation",
            "listItem3": "Enhance stakeholder engagement",
            "listItem4": "Measure and iterate",
            "listFollowup2": "By following these steps, organizations can achieve a more resilient operational model.",

            # --- Page 6 (Chapter 3) ---
            "sectionLabel5": "CHAPTER 03",
            "chapterLabel3": "03",
            "customTitle3": str(get_sec(2).get("title") or ""),
            "customContent3": str(get_sec(2).get("content") or ""),
            "imageLabel2": "OPERATIONAL VIEW",
            "imageCaption2": "Visualizing the components of successful execution.",
            "page6Stat1Value": "85%", "page6Stat1Desc": "Improvement in alignment",
            "page6Stat2Value": "2.4x", "page6Stat2Desc": "Increase in efficiency",
            "page6Stat3Value": "10k", "page6Stat3Unit": "+", "page6Stat3Desc": "Data points analyzed",
            "subheading3": "Framework",
            "subcontent3": "Our proven framework simplifies complex challenges into actionable strategic pillars.",
            "infoBoxLabel1": "QUICK TIP",
            "infoBoxContent1": "Always validate your assumptions against real-world performance metrics.",

            # --- Page 7 (Chapter 4) ---
            "sectionLabel6": "CHAPTER 04",
            "chapterLabel4": "04",
            "customTitle4": str(get_sec(3).get("title") or ""),
            "customContent4": str(get_sec(3).get("content") or ""),
            "colCard1Title": "INNOVATION", "colCard1Content": "Staying ahead requires a culture of continuous learning and adaptation.",
            "colCard2Title": "AGILITY", "colCard2Content": "The ability to pivot quickly is the ultimate competitive advantage.",
            "subheading4": "Best Practices",
            "subcontent4": "Consistency is the bridge between goals and accomplishment.",
            "calloutLabel2": "PRO TIP",
            "calloutContent2": "Automate routine tasks to free up cognitive bandwidth for high-value strategic work.",

            # --- Page 8 (Chapter 5) ---
            "sectionLabel7": "CHAPTER 05",
            "chapterLabel5": "05",
            "customTitle5": str(get_sec(4).get("title") or ""),
            "customContent5": str(get_sec(4).get("content") or ""),

            # --- Contact / CTA Page ---
            "ctaHeadlineLine1": "READY TO",
            "ctaHeadlineLine2": "TAKE ACTION?",
            "ctaEyebrow": "NEXT STEPS",
            "ctaTitle": str(cta_obj.get("headline") or "Start Your Journey"),
            "ctaText": str(cta_obj.get("description") or "We are ready to help you turn these insights into measurable growth."),
            "ctaButtonText": str(cta_obj.get("button_text") or "Connect Now"),
            "contactLabel1": "EMAIL", "contactValue1": email,
            "contactLabel2": "PHONE", "contactValue2": phone,
            "contactLabel3": "WEB", "contactValue3": website,
            "footerText": f"© {datetime.now().year} {company_name}",
        }

        # Logging for observability
        logger.info(f"📊 Template Mapping: {len(sections)} sections mapped. Title: '{main_title[:30]}...'")

        # Add page numbering and headers (standard for our templates)
        for i in range(1, 15):
            template_vars[f"headerText{i}"] = f"STEP 0{i}" if i < 10 else f"STEP {i}"
            template_vars[f"pageNumber{i+1}"] = i + 1
            template_vars[f"pageNumberHeader{i+1}"] = f"PAGE {i+1}"

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
                    "model": "sonar",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                },
                timeout=5
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

import os
from pathlib import Path
import json
import requests
import re
from typing import Dict, Any, Optional, List, Tuple
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
            print("❌ PERPLEXITY_API_KEY missing")
            raise Exception("PERPLEXITY_API_KEY is not configured")

        model_to_use = "sonar"
        try:
            print(f"Generating AI content with signals (15s timeout)...")
            
            # Log which fields are being inferred vs reinterpreted
            inferred = [k for k, v in signals.items() if v == "INFER_FROM_CONTEXT"]
            reinterpreted = [k for k, v in signals.items() if v.startswith("REINTERPRET")]
            print(f"📊 AI Signal Mapping: Inferred: {inferred} | Reinterpreted: {reinterpreted}")

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
                                "content": "You are an expert professional content generator. You only output valid JSON."
                            },
                            {
                                "role": "user",
                                "content": self._create_content_prompt(signals, firm_profile)
                            }
                        ],
                        "max_tokens": 2500,
                        "temperature": 0.7
                    },
                    timeout=15
                )
        except requests.exceptions.Timeout:
            print("❌ Perplexity API timeout (15s)")
            raise Exception("AI content generation timed out (15s limit). Please try again.")
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
        Robustly extract JSON from markdown or plain text.
        Handles cases where JSON is wrapped in code blocks or has surrounding text.
        """
        if not content:
            return ""
            
        content = content.strip()
        
        # Try regex to find JSON object or array
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', content)
        if json_match:
            return json_match.group(1)
            
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
            "placeholder", "asdf", "qwerty", "lorem", "ipsum", "...", "h", "ok."
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
                    "content": "A substantial, professional paragraph (min 60 words) providing deep insight.",
                    "subsections": [
                        {{"title": "Key Point", "content": "Professional detail"}}
                    ]
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
        
        IMPORTANT: Provide at least 5 deep-dive sections.
        """
        return prompt.strip()
        
    def normalize_ai_output(self, ai_result: Any) -> Dict[str, Any]:
        """
        Structural safety layer: Guarantees a safe schema for the PDF renderer.
        Flattens structures, joins paragraphs, and ensures string types.
        """
        if not isinstance(ai_result, dict):
            print(f"⚠️ AI Result is not a dict: {type(ai_result)}")
            ai_result = {}

        normalized = {
            "title": str(ai_result.get("title", "")).strip(),
            "summary": str(ai_result.get("summary", "")).strip(),
            "outcome_statement": str(ai_result.get("outcome_statement", "")).strip(),
            "key_insights": [],
            "sections": [],
            "call_to_action": {
                "headline": "",
                "description": "",
                "button_text": ""
            }
        }

        # 1. Normalize Key Insights
        raw_insights = ai_result.get("key_insights", [])
        if isinstance(raw_insights, list):
            normalized["key_insights"] = [str(i).strip() for i in raw_insights if i]

        # 2. Normalize Sections (Structural Safety)
        raw_sections = ai_result.get("sections", [])
        if not isinstance(raw_sections, list):
            raw_sections = []

        for idx, sec in enumerate(raw_sections):
            if not isinstance(sec, dict):
                continue
            
            # Guard keys and ensure strings
            sec_title = str(sec.get("title", "")).strip()
            raw_content = sec.get("content", "")
            
            # Join multi-paragraph content or lists into one safe string
            if isinstance(raw_content, list):
                sec_content = " ".join([str(p).strip() for p in raw_content if p])
            else:
                sec_content = str(raw_content).strip()

            # Remove markdown patterns that might break PDF renderer (e.g. ###, **, [links])
            sec_title = re.sub(r'#+\s*', '', sec_title)
            sec_title = re.sub(r'\*+', '', sec_title)
            sec_content = re.sub(r'#+\s*', '', sec_content)
            sec_content = re.sub(r'\*+', '', sec_content)
            
            normalized_sec = {
                "title": sec_title,
                "content": sec_content,
                "subsections": []
            }

            # Normalize Subsections
            raw_subs = sec.get("subsections", [])
            if isinstance(raw_subs, list):
                for sub in raw_subs:
                    if isinstance(sub, dict):
                        normalized_sec["subsections"].append({
                            "title": str(sub.get("title", "")).strip(),
                            "content": str(sub.get("content", "")).strip()
                        })
            
            normalized["sections"].append(normalized_sec)

        # 3. Normalize Call to Action
        raw_cta = ai_result.get("call_to_action", {})
        if isinstance(raw_cta, dict):
            normalized["call_to_action"]["headline"] = str(raw_cta.get("headline", "")).strip()
            normalized["call_to_action"]["description"] = str(raw_cta.get("description", "")).strip()
            normalized["call_to_action"]["button_text"] = str(raw_cta.get("button_text", "")).strip()

        print(f"✅ AI Normalization Complete: {len(normalized['sections'])} sections secured.")
        return normalized

    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Optional[Dict[str, Any]] = None,
        user_answers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Safely map AI generated JSON content to template variables."""
        # 0. Safety Guard: Ensure ai_content is already normalized or at least a dict
        if not isinstance(ai_content, dict):
            print("⚠️ map_to_template_vars: ai_content is not a dict, using empty dict")
            ai_content = {}

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
        
        # 3. Content Extraction from Structured AI JSON
        sections = ai_content.get("sections", [])
        if not isinstance(sections, list): 
            print("⚠️ map_to_template_vars: sections is not a list")
            sections = []
        
        # Helper for safe section access
        def get_sec(idx):
            if idx < len(sections):
                s = sections[idx]
                return s if isinstance(s, dict) else {}
            return {}

        def get_sub(sec_idx, sub_idx):
            sec = get_sec(sec_idx)
            subs = sec.get("subsections", [])
            if isinstance(subs, list) and sub_idx < len(subs):
                sub = subs[sub_idx]
                return sub if isinstance(sub, dict) else {}
            return {}

        # 4. Core Mapping
        def clean_sig(s):
            if not isinstance(s, str): return ""
            return s.replace("REINTERPRET: ", "") if s.startswith("REINTERPRET") else s

        main_title = str(ai_content.get("title") or clean_sig(user_answers.get("main_topic")) or "Expert Guide").strip()
        summary = str(ai_content.get("summary") or clean_sig(user_answers.get("desired_outcome")) or "Professional Insights").strip()
        
        # Split title for cover lines safely
        title_parts = main_title.split(":", 1)
        headline_1 = title_parts[0].strip()
        headline_2 = title_parts[1].strip() if len(title_parts) > 1 else "Executive Guide"

        # Extract CTA parts
        cta_obj = ai_content.get("call_to_action", {})
        if not isinstance(cta_obj, dict): cta_obj = {}

        template_vars = {
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
            
            # Cover Page mapping
            "coverSeriesLabel": "STRATEGIC REPORT",
            "coverEyebrow": "EXCLUSIVE INSIGHTS",
            "coverHeadlineLine1": headline_1,
            "coverHeadlineLine2": headline_2,
            "coverHeadlineLine3": company_name,
            "coverTagline": str(ai_content.get("outcome_statement") or summary).strip(),
            
            # Page 1 stats (synthesized or generic)
            "stat1Value": "100%", "stat1Label": "PROFESSIONAL",
            "stat2Value": "AI", "stat2Label": "DRIVEN",
            "stat3Value": "2024", "stat3Label": "EDITION",

            # Section Titles
            "sectionTitle1": "Introduction",
            "sectionTitle2": "Strategic Overview",
            "sectionTitle3": str(get_sec(0).get("title") or "Foundations"),
            "sectionTitle4": str(get_sec(1).get("title") or "Key Strategy"),
            "sectionTitle5": str(get_sec(2).get("title") or "Implementation"),
            "sectionTitle6": str(get_sec(3).get("title") or "Best Practices"),
            "sectionTitle7": str(get_sec(4).get("title") or "Next Steps"),
            
            # Chapter Labels
            "chapterLabel1": "CHAPTER 01",
            "chapterLabel2": "CHAPTER 02",
            "chapterLabel3": "CHAPTER 03",
            
            # Section Content - Guarding missing keys and ensuring string types
            "customTitle1": str(get_sec(0).get("title") or ""),
            "customContent1": str(get_sec(0).get("content") or ""),
            "customTitle2": str(get_sec(1).get("title") or "Key Strategy"),
            "customContent2": str(get_sec(1).get("content") or ""),
            "customTitle3": str(get_sec(2).get("title") or "Implementation"),
            "customContent3": str(get_sec(2).get("content") or ""),
            "customTitle4": str(get_sec(3).get("title") or "Best Practices"),
            "customContent4": str(get_sec(4).get("content") or ""), # Using section 5 for content 4
            "customTitle5": str(get_sec(4).get("title") or "Next Steps"),
            "customContent5": str(get_sec(4).get("content") or ""),
            
            # Sub-content / Boxes
            "subheading1": str(get_sub(0, 0).get("title") or "Core Insight"),
            "subcontent1": str(get_sub(0, 0).get("content") or ""),
            "calloutLabel1": "KEY TAKEAWAY",
            "calloutContent1": str(get_sub(0, 1).get("content") or "Focus on strategic alignment for maximum impact."),
            
            "subheading2": str(get_sub(1, 0).get("title") or "Analysis"),
            "subcontent2": str(get_sub(1, 0).get("content") or ""),
            "pullQuote1": str((ai_content.get("key_insights") or ["Strategy is the bridge between intent and results"])[0]),
            
            "subheading3": str(get_sub(2, 0).get("title") or "Framework"),
            "subcontent3": str(get_sub(2, 0).get("content") or ""),
            "infoBoxLabel1": "QUICK TIP",
            "infoBoxContent1": "Measure success through iterative feedback loops.",

            # Contact / CTA Page
            "ctaHeadlineLine1": "READY TO",
            "ctaHeadlineLine2": "TAKE ACTION?",
            "ctaEyebrow": "NEXT STEPS",
            "ctaTitle": str(cta_obj.get("headline") or "Partner with Us"),
            "ctaText": str(cta_obj.get("description") or "We help you turn these insights into measurable growth."),
            "ctaButtonText": str(cta_obj.get("button_text") or "Get Started"),
            "contactLabel1": "EMAIL", "contactValue1": email,
            "contactLabel2": "PHONE", "contactValue2": phone,
            "contactLabel3": "WEB", "contactValue3": website,
            "footerText": f"© {datetime.now().year} {company_name}",
        }

        # Logging for observability
        print(f"📊 Template Mapping: {len(sections)} sections mapped. Title: '{main_title[:30]}...'")

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

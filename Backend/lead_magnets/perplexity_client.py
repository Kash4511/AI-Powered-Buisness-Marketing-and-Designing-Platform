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
        
    def generate_lead_magnet_json(self, cleaned_data: Dict[str, Any], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            print("❌ PERPLEXITY_API_KEY missing")
            raise Exception("PERPLEXITY_API_KEY is not configured; cannot generate AI content. Please add PERPLEXITY_API_KEY=your_key_here to your Backend/.env file")

        # Render 30s limit requires fast AI. 
        model_to_use = "sonar" # Switch to sonar for speed to avoid 502s
        try:
            print(f"Generating AI content with model: {model_to_use} (15s timeout)...")

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
                                "content": self._create_content_prompt(cleaned_data, firm_profile)
                            }
                        ],
                        "max_tokens": 2500, # Lower token count = faster generation
                        "temperature": 0.7
                    },
                    timeout=15 # Hard limit for AI
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


    def _is_meaningful(self, value: Any) -> bool:
        """
        Strict check for meaningful user input.
        Returns True if the input has real semantic weight.
        """
        if not value:
            return False
        v = str(value).strip()
        if not v:
            return False
        
        # Rule: string length >= 4
        if len(v) < 4:
            return False
            
        # Common placeholder/filler check
        lowered = v.lower()
        fillers = {
            "test", "testing", "none", "n/a", "na", "null", "empty", "ok", "yes", "no", 
            "placeholder", "asdf", "qwerty", "lorem", "ipsum", "..."
        }
        if lowered in fillers:
            return False

        # Rule: Not repetitive characters (e.g. "aaaa")
        if len(set(lowered)) <= 2 and len(lowered) > 4:
            return False
            
        # Rule: Contains at least one "real word" (alphanumeric block)
        if not re.search(r'[A-Za-z0-9]{3,}', v):
            return False
            
        return True

    def get_semantic_data(self, user_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Splits user answers into cleaned_data (meaningful) and ignored_fields.
        """
        cleaned_data = {}
        ignored_fields = []
        
        for key, value in user_answers.items():
            if self._is_meaningful(value):
                cleaned_data[key] = value
            else:
                ignored_fields.append(key)
                
        return {
            "cleaned_data": cleaned_data,
            "ignored_fields": ignored_fields
        }

    def _create_content_prompt(self, cleaned_data: Dict[str, Any], firm_profile: Dict[str, Any]) -> str:
        """
        Builds a prompt from context. If a field is missing (ignored), 
        the AI is instructed to synthesize it from other signals.
        """
        # Core Context
        main_topic = cleaned_data.get('main_topic', 'Professional Design & Strategy')
        lm_type = cleaned_data.get('lead_magnet_type', 'Expert Guide')
        audience = cleaned_data.get('target_audience', 'Industry Professionals')
        pains = cleaned_data.get('audience_pain_points', [])
        
        # Optional Context
        desired_outcome = cleaned_data.get('desired_outcome')
        cta = cleaned_data.get('call_to_action')

        prompt = f"""
        You are a senior expert content strategist. Generate a high-value, professional {lm_type} about "{main_topic}".
        
        OBJECTIVE:
        Generate professional lead-magnet content. Use the provided context to synthesize a complete report.
        If certain fields are missing, infer them professionally based on the Topic ({main_topic}) and Audience ({audience}).
        
        STRICT RULES:
        1. REINTERPRET Meaningful Fields: Do not copy user input verbatim. Expand, professionalize, and elevate the language.
        2. CONTEXTUAL SYNTHESIS: 
           - If Desired Outcome is missing, derive it from the Topic + Audience pain points.
           - If CTA is missing, create a contextual, high-converting next step tied to the Topic.
        3. NO PROSE/MARKDOWN: Return valid JSON ONLY.
        4. NO PLACEHOLDERS: Generate expert-level insights. Never use "test" or generic text.
        
        CONTEXT:
        - Topic: {main_topic}
        - Audience: {audience}
        - Pain Points: {', '.join(pains) if isinstance(pains, list) else pains}
        - Desired Outcome: {desired_outcome if desired_outcome else 'Infer from context'}
        - Call to Action: {cta if cta else 'Derive contextual CTA'}
        - Firm: {firm_profile.get('firm_name', 'Expert Firm')}
        
        SCHEMA:
        {{
            "title": "Professional Document Title",
            "summary": "High-level executive summary (2-3 sentences)",
            "sections": [
                {{
                    "title": "Section Title",
                    "content": "Detailed, professional paragraph (minimum 60 words)",
                    "subsections": [
                        {{"title": "Sub-point", "content": "Professional insight"}}
                    ]
                }}
            ],
            "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
            "outcome_statement": "Concrete value proposition",
            "call_to_action": {{
                "headline": "Action Headline",
                "description": "Why take this step",
                "button_text": "Action verb"
            }},
            "style": {{
                "primary_color": "{firm_profile.get('primary_brand_color', '#2a5766')}",
                "secondary_color": "{firm_profile.get('secondary_brand_color', '#ffffff')}"
            }}
        }}
        
        IMPORTANT: Provide at least 5 sections. Each section's 'content' should be a substantial professional paragraph.
        """
        return prompt.strip()
        
    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Optional[Dict[str, Any]] = None,
        user_answers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Safely map AI generated JSON content to template variables."""
        if not isinstance(ai_content, dict):
            ai_content = {}

        firm_profile = firm_profile or {}
        user_answers = user_answers or {}
        
        # 1. Basic Metadata
        company_name = firm_profile.get("firm_name", "Expert Firm")
        email = firm_profile.get("work_email", "")
        phone = firm_profile.get("phone_number", "")
        website = firm_profile.get("firm_website", "")
        logo_url = firm_profile.get("logo_url", "")
        
        # 2. Colors & Style
        primary_color = firm_profile.get("primary_brand_color") or "#2a5766"
        secondary_color = firm_profile.get("secondary_brand_color") or "#ffffff"
        accent_color = "#F4A460"
        
        # 3. Content Extraction from Structured AI JSON
        sections = ai_content.get("sections", [])
        if not isinstance(sections, list): sections = []
        
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
        template_vars = {
            "mainTitle": ai_content.get("title") or user_answers.get("main_topic") or "Expert Guide",
            "documentTitle": (ai_content.get("title") or user_answers.get("main_topic") or "Expert Guide").upper(),
            "documentSubtitle": ai_content.get("summary") or user_answers.get("desired_outcome") or "Professional Insights",
            "companyName": company_name,
            "primaryColor": primary_color,
            "secondaryColor": secondary_color,
            "accentColor": accent_color,
            "logoUrl": logo_url,
            "emailAddress": email,
            "phoneNumber": phone,
            "website": website,
            "leadMagnetDescription": ai_content.get("summary", ""),
            
            # Section Titles
            "sectionTitle3": get_sec(0).get("title", "Overview"),
            "sectionTitle4": get_sec(1).get("title", "Key Strategy"),
            "sectionTitle5": get_sec(2).get("title", "Implementation"),
            "sectionTitle6": get_sec(3).get("title", "Best Practices"),
            "sectionTitle7": get_sec(4).get("title", "Next Steps"),
            
            # Section Content
            "customTitle1": get_sec(0).get("title", ""),
            "customContent1": get_sec(0).get("content", ""),
            "customTitle2": get_sec(1).get("title", "Key Strategy"),
            "customContent2": get_sec(1).get("content", ""),
            "customTitle3": get_sec(2).get("title", "Implementation"),
            "customContent3": get_sec(2).get("content", ""),
            "customTitle4": get_sec(3).get("title", "Best Practices"),
            "customContent4": get_sec(3).get("content", ""),
            "customTitle5": get_sec(4).get("title", "Next Steps"),
            "customContent5": get_sec(4).get("content", ""),
            
            # Sub-content / Boxes
            "subheading1": get_sub(0, 0).get("title", ""),
            "subcontent1": get_sub(0, 0).get("content", ""),
            "accentBoxTitle1": get_sub(0, 0).get("title", "Key Insight"),
            "accentBoxContent1": get_sub(0, 0).get("content", ""),
            
            "subheading2": get_sub(1, 0).get("title", ""),
            "subcontent2": get_sub(1, 0).get("content", ""),
            
            "subheading3": get_sub(2, 0).get("title", ""),
            "subcontent3": get_sub(2, 0).get("content", ""),
            
            # Contact / CTA
            "contactTitle": ai_content.get("call_to_action", {}).get("headline", "Next Steps"),
            "contactDescription": ai_content.get("call_to_action", {}).get("description", ""),
            "ctaText": ai_content.get("call_to_action", {}).get("button_text", "Get Started"),
        }
        
        # Add page numbering and headers (standard for our templates)
        for i in range(1, 9):
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

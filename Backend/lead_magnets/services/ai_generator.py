import os
import json
import logging
import time
from pathlib import Path
from groq import Groq

# Attempt to load .env for local development / background threads
try:
    from dotenv import load_dotenv
    # Look for .env in the Backend directory (parent of services/..)
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

logger = logging.getLogger(__name__)

class LeadMagnetAIService:
    """
    Service for generating high-quality business lead magnet content using Groq and Llama-3.1-8B-Instant.
    """

    def __init__(self):
        # Prioritize GROQ_API_KEY
        api_key = os.getenv("GROQ_API_KEY")
        
        # Fallback to the misconfigured key name if present
        if not api_key:
            api_key = os.getenv("GROQ_API_KEY_API_KEY")
            
        if not api_key:
            logger.error("❌ GROQ_API_KEY is missing from environment variables.")
            raise ValueError(
                "GROQ_API_KEY is required for AI content generation. "
                "If you are on Render, add this key to your environment variables in the dashboard. "
                "If local, ensure it is set in Backend/.env"
            )
            
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.1-8b-instant"
        self.temperature = 0.4
        self.max_tokens = 1500

    def generate_lead_magnet(self, data: dict) -> dict:
        """
        Generates lead magnet content based on provided input data.
        Includes one automatic retry for JSON parsing failures.
        """
        prompt = self._construct_prompt(data)
        system_prompt = self._get_system_prompt()

        try:
            return self._call_ai(system_prompt, prompt)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"⚠️ AI response parsing failed: {str(e)}. Retrying...")
            try:
                # One-time retry
                return self._call_ai(system_prompt, prompt)
            except Exception as retry_err:
                logger.error(f"❌ AI Generation failed after retry: {str(retry_err)}")
                raise ValueError(f"AI content generation failed: {str(retry_err)}")

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> dict:
        logger.info(f"Groq API Call: model={self.model}, max_tokens={max_tokens or self.max_tokens}")
        logger.debug(f"Groq System Prompt: {system_prompt[:500]}...")
        logger.debug(f"Groq User Prompt: {user_prompt[:500]}...")
        
        start_time = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            response_format={"type": "json_object"}
        )
        duration = time.time() - start_time
        logger.info(f"Groq API Response received in {duration:.2f}s")

        raw_content = response.choices[0].message.content
        if not raw_content:
            logger.error("❌ Groq API returned an empty response")
            raise ValueError("Empty response from Groq API")

        logger.info(f"Groq Raw Content Length: {len(raw_content)} characters")
        logger.debug(f"Groq Raw Content Snippet: {raw_content[:1000]}...")

        # Basic cleanup in case AI adds markdown fences despite response_format
        cleaned_content = self._clean_json_string(raw_content)
        
        try:
            parsed_json = json.loads(cleaned_content)
            logger.info("✅ Groq JSON parsed successfully")
            return parsed_json
        except json.JSONDecodeError as e:
            logger.error(f"❌ Groq JSON Decode Error: {str(e)}")
            logger.error(f"Problematic JSON string: {cleaned_content[:2000]}...")
            raise e

    def _clean_json_string(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def is_substantive(self, text, min_words=600) -> bool:
        """Checks if the provided text meets the minimum word count requirement."""
        if not text:
            return False
        return len(str(text).split()) >= min_words

    def expand_content_sections(self, base_content: dict, data: dict) -> dict:
        """
        Takes the base AI response and generates expanded, technical content for each chapter 
        to ensure no page is left blank or generic.
        """
        main_topic = data.get("main_topic", "Business Strategy")
        target_audience = data.get("target_audience", "Executives")
        pain_points = data.get("pain_points", [])
        
        expansion_system_prompt = f"""You are generating a 15-page institutional-grade technical strategic report. 

This is NOT a summary. This is a dense, fully written document suitable for executive review. 

STRICT INPUT ALIGNMENT: 
Every chapter MUST reference and address: 
- MAIN TOPIC: {main_topic}
- TARGET AUDIENCE: {target_audience}
- PAIN POINTS: {pain_points}

Content Requirements: 
- Total document MUST be exactly 15 pages when rendered.
- Each page MUST be visually full.
- Each chapter MUST contain at least 1500 words of continuous body text.
- Professional, strategic, consulting-level insight (McKinsey/BCG style). 
- Include technical terminology, quantified metrics, and operational depth. 
- NO generic filler, NO empty boxes, NO shallow summaries. 

Image Placeholders: 
- Insert exactly 2 placeholders per chapter using: [IMAGE_PLACEHOLDER: detailed strategic description]
- These will be replaced by actual project images provided by the user.

Structure: 
- Executive Summary: 800 words of dense strategic overview.
- Chapter 1: Problem Landscape (Analyze pain points deeply in context of {main_topic})
- Chapter 2: Strategic Framework (Actionable solutions for {target_audience})
- Chapter 3: Implementation Roadmap (Step-by-step process)
- Chapter 4: Success Benchmarks & Case Studies (Realistic examples)
- Chapter 5: Engagement Methods & Strategic Takeaways

Return JSON with these exact keys: 
{{ 
  "executive_summary": "800-word dense executive summary",
  "chapter_1": {{
    "eyebrow": "Strategic Context",
    "section_id": "CH 01",
    "title": "THE CHALLENGE LANDSCAPE",
    "intro": "400-word technical intro",
    "body": "1500-word technical body with exactly 2 [IMAGE_PLACEHOLDER: ...] entries",
    "impact_label": "Economic Impact",
    "impact_value": "Quantified impact analysis"
  }},
  "chapter_2": {{
    "eyebrow": "Strategic Solution",
    "section_id": "CH 02",
    "title": "ACTIONABLE FRAMEWORKS",
    "intro": "400-word technical intro",
    "body": "1500-word technical body with exactly 2 [IMAGE_PLACEHOLDER: ...] entries",
    "intervention_labels": ["Operational", "Financial", "Strategic"]
  }},
  "chapter_3": {{
    "eyebrow": "Execution Pathway",
    "section_id": "CH 03",
    "title": "IMPLEMENTATION ROADMAP",
    "intro": "400-word technical intro",
    "phase_1": {{"title": "Phase I: Discovery", "desc": "600-word detailed integration step"}},
    "phase_2": {{"title": "Phase II: Scale", "desc": "600-word detailed optimization step"}},
    "body": "1500-word technical body with exactly 2 [IMAGE_PLACEHOLDER: ...] entries"
  }},
  "chapter_4": {{
    "eyebrow": "Market Benchmarks",
    "section_id": "CH 04",
    "title": "REALISTIC CASE STUDIES",
    "intro": "400-word technical intro",
    "case_study_1": {{"title": "Global Implementation", "desc": "800-word case study", "result": "25% ROI Increase"}},
    "case_study_2": {{"title": "Regional Optimization", "desc": "800-word case study", "result": "40% Risk Reduction"}},
    "body": "1500-word technical body with exactly 2 [IMAGE_PLACEHOLDER: ...] entries"
  }},
  "chapter_5": {{
    "eyebrow": "Strategic Methodologies",
    "section_id": "CH 05",
    "title": "ENGAGEMENT & TAKEAWAYS",
    "intro": "400-word technical intro",
    "methods": [
       {{"phase": "Strategic Audit", "desc": "Detailed audit methodology"}},
       {{"phase": "Framework Design", "desc": "Custom design process"}},
       {{"phase": "Change Management", "desc": "Implementation strategy"}},
       {{"phase": "Performance Monitoring", "desc": "KPI tracking"}},
       {{"phase": "Continuous Improvement", "desc": "Scaling roadmap"}}
    ],
    "body": "1500-word technical body with exactly 2 [IMAGE_PLACEHOLDER: ...] entries"
  }},
  "roi_detailed_analysis": "1000-word detailed ROI prose", 
  "conclusion_strategy": "1000-word dense strategic conclusion",
  "drop_caps": ["S", "F", "C", "M", "T"],
  "image_labels": ["CHALLENGE ANALYSIS", "SOLUTION FRAMEWORK", "EXECUTION PATHWAY", "BENCHMARK DATA", "METHODOLOGY"]
}} 

Rules: 
- Return valid JSON only. 
- TOTAL word count MUST exceed 8000 words. 
- Deeply align all content with {main_topic}, {target_audience}, and {pain_points}.
"""

        expansion_user_prompt = f"""Expand the following lead magnet structure into a detailed 20-page technical report.
TOPIC: {main_topic}
AUDIENCE: {target_audience}
PAIN POINTS: {pain_points}

BASE STRUCTURE:
{json.dumps(base_content, indent=2)}

Ensure all content is technical, data-driven, and addresses the audience's specific pain points deeply."""

        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"🚀 AI Expansion Attempt {attempt + 1}")
                # Increased max_tokens significantly for dense content
                # Groq has limits, we might need multiple calls if this is too large
                # but let's try 8192 first (max for some llama models)
                expanded = self._call_ai(expansion_system_prompt, expansion_user_prompt, max_tokens=8192)
                
                # Validation Layer
                is_valid = True
                chapters_to_check = ['chapter_1', 'chapter_2', 'chapter_3', 'chapter_4', 'chapter_5']
                
                total_words = 0
                for ch in chapters_to_check:
                    ch_data = expanded.get(ch, {})
                    content = ch_data.get('body', "")
                    word_count = len(str(content).split())
                    total_words += word_count
                    if not self.is_substantive(content, min_words=600):
                        logger.warning(f"⚠️ {ch} body is not substantive enough ({word_count} words).")
                        is_valid = False
                        break
                
                logger.info(f"📊 Total word count across chapters: {total_words}")
                
                if is_valid and total_words >= 3000: # Heuristic for total depth
                    logger.info("✅ AI Expansion passed substantive validation.")
                    base_content['expansions'] = expanded
                    return base_content
                
                if attempt == max_retries - 1:
                    logger.error("❌ AI Expansion failed substantive validation after max retries.")
                    base_content['expansions'] = expanded # Still return it as best effort
                    
            except Exception as e:
                logger.error(f"⚠️ AI Expansion failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return base_content
                    
        return base_content

    def _get_system_prompt(self) -> str:
        return """You are a senior business strategist and conversion copywriter. 
Your goal is to generate high-value, institutional-grade lead magnet content.

RULES:
- NO fluff.
- NO generic marketing language.
- NO storytelling.
- NO motivational tone.
- NO introductions.
- NO conclusions.
- NO markdown.
- NO explanations outside the JSON.
- Return STRICTLY valid JSON only.
- Follow the schema exactly.
- Do not add extra fields.
- Be concise but complete.

SCHEMA:
{
  "title": "Professional Document Title",
  "subtitle": "Strategic value proposition",
  "target_audience_summary": "Concise definition of the ideal reader profile",
  "audience_analysis": {
    "commercial_label": "Commercial Clients",
    "commercial_text": "Regulatory alignment...",
    "government_label": "Government Authorities",
    "government_text": "Policy integration...",
    "architect_label": "Architects",
    "architect_text": "Technical coordination...",
    "contractor_label": "Contractors",
    "contractor_text": "Execution efficiency..."
  },
  "key_pain_points": [
    {
      "title": "Specific problem name",
      "description": "Technical or business impact"
    }
  ],
  "solutions": [
    {
      "title": "Strategic solution name",
      "implementation_steps": [
        "Step 1",
        "Step 2"
      ],
      "expected_outcome": "Quantifiable benefit"
    }
  ],
  "roi_section": {
    "cost_savings": "Estimated financial impact",
    "time_savings": "Efficiency gains",
    "competitive_advantage": "Market positioning benefit"
  },
  "call_to_action": "Clear, professional next step"
}"""

    def _construct_prompt(self, data: dict) -> str:
        main_topic = data.get("main_topic", "Business Strategy")
        
        target_audience = data.get("target_audience", "Executives")
        if isinstance(target_audience, list):
            target_audience = ", ".join(target_audience)
            
        pain_points = data.get("pain_points", [])
        if isinstance(pain_points, list):
            pain_points = ", ".join(pain_points)
            
        tone = data.get("tone", "Professional")
        
        return f"""Generate lead magnet content for the following profile:
TOPIC: {main_topic}
AUDIENCE: {target_audience}
PAIN POINTS: {pain_points}
TONE: {tone}

Ensure all content is technical, data-driven, and provides immediate strategic value."""

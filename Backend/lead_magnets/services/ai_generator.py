import os
import json
import logging
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

    def _call_ai(self, system_prompt: str, user_prompt: str) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content
        if not raw_content:
            raise ValueError("Empty response from Groq API")

        # Basic cleanup in case AI adds markdown fences despite response_format
        cleaned_content = self._clean_json_string(raw_content)
        return json.loads(cleaned_content)

    def _clean_json_string(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def expand_content_sections(self, base_content: dict, data: dict) -> dict:
        """
        Takes the base AI response and generates expanded, technical content for each chapter 
        to ensure no page is left blank or generic.
        """
        main_topic = data.get("main_topic", "Business Strategy")
        target_audience = data.get("target_audience", "Executives")
        
        expansion_prompt = f"""You are a senior institutional consultant. 
Expand the following lead magnet structure into a detailed 8-page technical report.
TOPIC: {main_topic}
AUDIENCE: {target_audience}

BASE STRUCTURE:
{json.dumps(base_content, indent=2)}

REQUIREMENTS:
1. Generate a 'chapter_expansions' object.
2. For each expansion, provide:
   - 'detailed_analysis': 300 words of technical, data-heavy analysis.
   - 'quantified_impact': Specific metrics (e.g. "22% reduction in Opex").
   - 'case_study': A realistic institutional example.
3. Chapters to expand: 'Strategic Challenges', 'Technical Solutions', 'Implementation Framework'.

JSON ONLY. NO MARKDOWN. NO FLUFF."""

        try:
            expanded = self._call_ai(self._get_system_prompt(), expansion_prompt)
            base_content['expansions'] = expanded.get('chapter_expansions', {})
            return base_content
        except Exception as e:
            logger.error(f"⚠️ AI Expansion failed: {e}")
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
  "key_pain_points": [
    {
      "title": "Specific problem name",
      "description": "Technical or business impact of this problem"
    }
  ],
  "solutions": [
    {
      "title": "Strategic solution name",
      "implementation_steps": [
        "Step 1: Actionable item",
        "Step 2: Actionable item"
      ],
      "expected_outcome": "Quantifiable or strategic benefit"
    }
  ],
  "roi_section": {
    "cost_savings": "Estimated financial impact or formula",
    "time_savings": "Efficiency gains description",
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

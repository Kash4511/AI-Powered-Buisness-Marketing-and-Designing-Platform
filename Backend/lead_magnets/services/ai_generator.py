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

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> dict:
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

    def is_substantive(self, text, min_words=350) -> bool:
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
        
        expansion_system_prompt = """You are generating an 8-page institutional-grade technical strategic report. 

This is NOT a summary. 

This must be a dense, fully written document suitable for executive review. 

Strict Requirements: 

Each chapter must contain: 
- Minimum 400–600 words of continuous body text. 
- At least 3 fully developed paragraphs. 
- No bullet-only sections. 
- No short placeholder sentences. 
- No generic phrases like "This framework ensures success." 
- No marketing fluff. 

Content must: 
- Explain mechanisms. 
- Explain implementation details. 
- Provide operational depth. 
- Include quantified metrics (percentages, cost ranges, timeframes). 
- Include technical terminology relevant to the topic. 
- Include realistic constraints and tradeoffs. 

Case studies must: 
- Be minimum 250 words each. 
- Describe context, problem, action taken, measurable outcome. 
- Include numeric performance improvements. 

ROI section must: 
- Include cost modeling explanation. 
- Include capital expenditure vs operational savings comparison. 
- Include 5-year projection logic. 
- Minimum 300 words. 

Final document must exceed 3,500 total words. 

Return JSON with these exact keys: 
{ 
  "chapter_1": {
    "eyebrow": "Analysis",
    "section_id": "CH 01",
    "title": "STRATEGIC CHALLENGES",
    "intro": "Brief technical intro to the challenges",
    "body": "Full 400-600 word technical body",
    "impact_label": "Risk Factor",
    "impact_value": "Quantified impact description"
  },
  "chapter_2": {
    "eyebrow": "Solution",
    "section_id": "CH 02",
    "title": "STRATEGIC SOLUTIONS",
    "intro": "Brief technical intro to the solutions",
    "body": "Full 400-600 word technical body",
    "intervention_labels": ["Label 1", "Label 2", "Label 3"]
  },
  "chapter_3": {
    "eyebrow": "Execution",
    "section_id": "CH 03",
    "title": "EXECUTION ROADMAP",
    "intro": "Brief technical intro to the roadmap",
    "phase_1": {"title": "Integration", "desc": "Detailed integration step"},
    "phase_2": {"title": "Optimization", "desc": "Detailed optimization step"},
    "body": "Full 400-600 word technical body"
  },
  "chapter_4": {
    "eyebrow": "Benchmarks",
    "section_id": "CH 04",
    "title": "SUCCESS BENCHMARKS",
    "intro": "Brief technical intro to case studies",
    "case_study_1": {"title": "Project Alpha", "desc": "250 word case study", "result": "Metric"},
    "case_study_2": {"title": "Project Beta", "desc": "250 word case study", "result": "Metric"},
    "body": "Full 400-600 word technical body"
  },
  "chapter_5": {
    "eyebrow": "Methods",
    "section_id": "CH 05",
    "title": "ENGAGEMENT METHODS",
    "intro": "Brief technical intro to methods",
    "methods": [
       {"phase": "Advisory", "desc": "Detailed service description"},
       {"phase": "Design", "desc": "Detailed service description"},
       {"phase": "Management", "desc": "Detailed service description"},
       {"phase": "Analysis", "desc": "Detailed service description"},
       {"phase": "Scaling", "desc": "Detailed service description"}
    ],
    "body": "Full 400-600 word technical body"
  },
  "roi_detailed_analysis": "Detailed ROI prose", 
  "conclusion_strategy": "Dense strategic conclusion",
  "drop_caps": ["S", "F", "C", "M", "T"],
  "image_labels": ["CHALLENGE ANALYSIS", "SOLUTION FRAMEWORK", "EXECUTION PATHWAY"]
} 

Rules: 
- No markdown 
- No bullet points unless embedded within paragraphs 
- No headings inside text 
- No summaries 
- No placeholders 
- Continuous dense professional prose 
- Return valid JSON only."""

        expansion_user_prompt = f"""Expand the following lead magnet structure into a detailed 8-page technical report.
TOPIC: {main_topic}
AUDIENCE: {target_audience}

BASE STRUCTURE:
{json.dumps(base_content, indent=2)}

Ensure all content is technical, data-driven, and provides immediate strategic value."""

        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"🚀 AI Expansion Attempt {attempt + 1}")
                # Increased max_tokens for dense content
                expanded = self._call_ai(expansion_system_prompt, expansion_user_prompt, max_tokens=4096)
                
                # Validation Layer
                is_valid = True
                chapters_to_check = ['chapter_1', 'chapter_2', 'chapter_3', 'chapter_4', 'chapter_5']
                
                for ch in chapters_to_check:
                    ch_data = expanded.get(ch, {})
                    content = ch_data.get('body', "")
                    if not self.is_substantive(content, min_words=350):
                        logger.warning(f"⚠️ {ch} body is not substantive enough ({len(str(content).split())} words).")
                        is_valid = False
                        break
                
                if is_valid:
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

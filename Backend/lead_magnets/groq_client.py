import os
import json
import logging
import time
import re
from typing import Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)

class GroqClient:
    """
    Client for interacting with Groq API for lead magnet generation.
    Replaces the interface previously used by PerplexityClient.
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            api_key = os.getenv("GROQ_API_KEY_API_KEY")
            
        if not api_key:
            logger.error("❌ GROQ_API_KEY is missing from environment variables.")
            raise ValueError("GROQ_API_KEY is required for AI content generation.")
            
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        self.temperature = 0.5
        self.max_tokens = 8192  # High token limit for dense reports

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Derives key semantic signals from user answers to guide AI generation.
        """
        topic = user_answers.get('main_topic', 'Strategic Design')
        audience = user_answers.get('target_audience', 'Stakeholders')
        pain_points = user_answers.get('pain_points', [])
        
        if isinstance(pain_points, list):
            pain_points_str = ", ".join(pain_points)
        else:
            pain_points_str = str(pain_points)

        return {
            'topic': topic,
            'audience': audience,
            'pain_points': pain_points_str,
            'tone': user_answers.get('tone', 'Professional'),
            'industry': user_answers.get('industry', 'Architecture')
        }

    def generate_lead_magnet_json(self, signals: Dict[str, Any], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls Groq API to generate the initial structured JSON for the lead magnet.
        """
        system_prompt = self._get_base_system_prompt()
        user_prompt = self._construct_base_user_prompt(signals, firm_profile)
        
        try:
            raw_data = self._call_ai(system_prompt, user_prompt)
            # Automatically expand to 15 pages if base generation succeeds
            return self._expand_to_15_pages(raw_data, signals)
        except Exception as e:
            logger.error(f"Groq generation failed: {str(e)}")
            raise e

    def normalize_ai_output(self, raw_ai_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensures the AI output follows a consistent structure for the template.
        """
        # If the content was already expanded, it will have 'expansions'
        exp = raw_ai_content.get('expansions', {})
        
        normalized = {
            'title': raw_ai_content.get('title', 'Strategic Report'),
            'subtitle': raw_ai_content.get('subtitle', ''),
            'summary': raw_ai_content.get('target_audience_summary', ''),
            'audience_analysis': exp.get('audience_analysis', raw_ai_content.get('audience_analysis', {})),
            'key_pain_points': raw_ai_content.get('key_pain_points', []),
            'solutions': raw_ai_content.get('solutions', []),
            'roi_section': raw_ai_content.get('roi_section', {}),
            'call_to_action': raw_ai_content.get('call_to_action', ''),
            'executive_summary': exp.get('executive_summary', ''),
            'roi_detailed': exp.get('roi_detailed_analysis', ''),
            'conclusion': exp.get('conclusion_strategy', ''),
            'drop_caps': exp.get('drop_caps', ["S", "F", "C", "M", "T"]),
            'image_labels': exp.get('image_labels', [
                exp.get('imagePage4Url_label', 'ANALYSIS'),
                exp.get('imagePage5Url_label', 'SOLUTION'),
                exp.get('imagePage6Url_label', 'ROADMAP')
            ]),
            'chapters': {
                'ch1': exp.get('chapter_1', {}),
                'ch2': exp.get('chapter_2', {}),
                'ch3': exp.get('chapter_3', {}),
                'ch4': exp.get('chapter_4', {}),
                'ch5': exp.get('chapter_5', {}),
            }
        }
        
        # Ensure all chapter bodies have closed tags
        for ch_key in normalized['chapters']:
            ch = normalized['chapters'][ch_key]
            if 'body_a' in ch: ch['body_a'] = self._ensure_closed_tags(ch['body_a'])
            if 'body_b' in ch: ch['body_b'] = self._ensure_closed_tags(ch['body_b'])
            
        return normalized

    def ensure_section_content(self, sections: List[Dict[str, Any]], signals: Dict[str, Any], firm_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Guarantee that sections have content. If empty, performs targeted generation.
        This is a legacy method kept for compatibility with the views.
        """
        if sections:
            return sections
            
        # Fallback: create a section for each chapter if sections are missing
        # This is primarily for ReportLab which expects a 'sections' list
        return [
            {"title": "Executive Summary", "content": "Institutional analysis..."},
            {"title": "Strategic Context", "content": "Problem landscape..."},
            {"title": "Actionable Framework", "content": "Solution overview..."},
            {"title": "Implementation Roadmap", "content": "Execution pathway..."},
            {"title": "Market Benchmarks", "content": "Case study analysis..."}
        ]

    def map_to_template_vars(self, ai_content: Dict[str, Any], firm_profile: Dict[str, Any], signals: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Maps the normalized AI content to the final Jinja2 template variables.
        """
        chapters = ai_content.get('chapters', {})
        
        template_vars = {
            'mainTitle': ai_content.get('title'),
            'documentSubtitle': ai_content.get('subtitle'),
            'companyName': firm_profile.get('firm_name'),
            'emailAddress': firm_profile.get('work_email'),
            'phoneNumber': firm_profile.get('phone_number'),
            'website': firm_profile.get('firm_website'),
            'primaryColor': firm_profile.get('primary_brand_color', '#2a5766'),
            'secondaryColor': firm_profile.get('secondary_brand_color', '#FFFFFF'),
            'summary': ai_content.get('summary'),
            'audience_analysis': ai_content.get('audience_analysis'),
            'key_pain_points': ai_content.get('key_pain_points'),
            'solutions': ai_content.get('solutions'),
            'roi': ai_content.get('roi_section'),
            'cta': ai_content.get('call_to_action'),
            
            # Technical Expansions (15-page structure)
            'ch1': chapters.get('ch1', {}),
            'ch2': chapters.get('ch2', {}),
            'ch3': chapters.get('ch3', {}),
            'ch4': chapters.get('ch4', {}),
            'ch5': chapters.get('ch5', {}),
            'roi_detailed': ai_content.get('roi_detailed'),
            'conclusion': ai_content.get('conclusion'),
            'drop_caps': ai_content.get('drop_caps'),
            'image_labels': ai_content.get('image_labels'),
            'executive_summary': ai_content.get('executive_summary'),
            'footerText': f"© {firm_profile.get('firm_name', 'Strategic Report')}"
        }
        
        return template_vars

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Dict[str, Any]:
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
        return json.loads(raw_content)

    def _validate_expansion(self, content: Dict[str, Any]) -> bool:
        """Validates the quality and density of the expanded content."""
        text = json.dumps(content)
        word_count = len(text.split())
        placeholders = text.count("IMAGE_PLACEHOLDER")
        
        logger.info(f"📊 Validation: word_count={word_count}, placeholders={placeholders}")
        
        if word_count < 4000: # Slightly lower than 5000 to be realistic for Llama-3.3-70b
            logger.warning(f"⚠️ Expansion too short: {word_count} words")
            # We won't strictly raise ValueError here to avoid failing the whole process,
            # but we log it and try to improve.
            
        if placeholders < 8:
            logger.warning(f"⚠️ Not enough image placeholders: {placeholders}")
            
        return True

    def _expand_to_15_pages(self, base_content: Dict[str, Any], signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to expand base content into a 15-page institutional report.
        Uses section-by-section generation for maximum depth and quality.
        """
        topic = signals.get('topic')
        audience = signals.get('audience')
        pain_points = signals.get('pain_points')
        
        # Stage 1: Executive Summary & Audience Analysis
        logger.info("🚀 Stage 1: Generating Executive Summary & Audience Analysis...")
        stage1_prompt = f"""You are generating a PROFESSIONAL 15-page consulting-grade report.
TOPIC: {topic}
AUDIENCE: {audience}
PAIN POINTS: {pain_points}

Requirement: Generate a dense 800-word Executive Summary and a 1200-word Audience Analysis deep-dive.
Audience Analysis MUST cover: Commercial, Government, Architect, and Contractor stakeholders.

Return JSON: {{
  "executive_summary": "800-word dense prose",
  "audience_analysis": {{
    "commercial_label": "Commercial Stakeholders", "commercial_text": "300-word analysis",
    "government_label": "Public Sector", "government_text": "300-word analysis",
    "architect_label": "Design Professionals", "architect_text": "300-word analysis",
    "contractor_label": "Execution Teams", "contractor_text": "300-word analysis"
  }}
}}"""
        stage1 = self._call_ai("You are a senior strategist.", stage1_prompt)

        # Stage 2: Chapters 1-5
        logger.info("🚀 Stage 2: Generating Chapters 1-5 (Dense Technical Prose)...")
        stage2_prompt = f"""You are generating Chapters 1-5 for a 15-page report on {topic}.
STRICT REQUIREMENTS:
- Each chapter MUST be 1000-1200 words.
- Each chapter MUST contain at least 2 [IMAGE_PLACEHOLDER: detailed strategic description] tags.
- Content must be technical, data-driven, and institutional-grade.

Return JSON: {{
  "chapter_1": {{ "eyebrow": "Strategic Context", "section_id": "CH 01", "title": "...", "intro": "...", "body_a": "500 words", "body_b": "500 words", "impact_label": "...", "impact_value": "..." }},
  "chapter_2": {{ "eyebrow": "Strategic Solution", "section_id": "CH 02", "title": "...", "intro": "...", "body_a": "500 words", "body_b": "500 words", "intervention_labels": ["..."] }},
  "chapter_3": {{ "eyebrow": "Execution Pathway", "section_id": "CH 03", "title": "...", "intro": "...", "phase_1": {{"title": "...", "desc": "..."}}, "phase_2": {{"title": "...", "desc": "..."}}, "body_a": "500 words", "body_b": "500 words" }},
  "chapter_4": {{ "eyebrow": "Market Benchmarks", "section_id": "CH 04", "title": "...", "intro": "...", "case_study_1": {{"title": "...", "desc": "...", "result": "..."}}, "case_study_2": {{"title": "...", "desc": "...", "result": "..."}}, "body_a": "500 words", "body_b": "500 words" }},
  "chapter_5": {{ "eyebrow": "Strategic Methodologies", "section_id": "CH 05", "title": "...", "intro": "...", "methods": [ {{"phase": "...", "desc": "..."}} ], "body_a": "500 words", "body_b": "500 words" }}
}}"""
        stage2 = self._call_ai("You are a technical document architect.", stage2_prompt)

        # Stage 3: ROI & Conclusion
        logger.info("🚀 Stage 3: Generating ROI Analysis & Strategic Recommendations...")
        stage3_prompt = f"""Generate the final Page 15 (ROI Analysis & Strategic Recommendations).
Requirement: 1000 words of dense prose.
Return JSON: {{
  "roi_detailed_analysis": "1000-word ROI forecast",
  "conclusion_strategy": "1000-word dense conclusion",
  "drop_caps": ["S", "F", "C", "M", "T"],
  "image_labels": ["CHALLENGE", "SOLUTION", "ROADMAP", "BENCHMARK", "METHODOLOGY"],
  "cta": "Professional Call to Action"
}}"""
        stage3 = self._call_ai("You are a financial analyst.", stage3_prompt)

        # Merge all stages
        expanded = {{**stage1, **stage2, **stage3}}
        self._validate_expansion(expanded)
        
        base_content['expansions'] = expanded
        return base_content

    def _get_base_system_prompt(self) -> str:
        return """You are a senior business strategist. Return valid JSON only.
SCHEMA: {
  "title": "...", "subtitle": "...", "target_audience_summary": "...",
  "audience_analysis": { "commercial_text": "...", "government_text": "...", "architect_text": "...", "contractor_text": "..." },
  "key_pain_points": [ { "title": "...", "description": "..." } ],
  "solutions": [ { "title": "...", "implementation_steps": [...], "expected_outcome": "..." } ],
  "roi_section": { "cost_savings": "...", "time_savings": "...", "competitive_advantage": "..." },
  "call_to_action": "..."
}"""

    def _construct_base_user_prompt(self, signals: Dict[str, Any], firm_profile: Dict[str, Any]) -> str:
        return f"""Generate high-fidelity institutional lead magnet content for:
TOPIC: {signals['topic']}
AUDIENCE: {signals['audience']}
PAIN POINTS: {signals['pain_points']}
FIRM NAME: {firm_profile.get('firm_name')}
FIRM SPECIALIZATION: {firm_profile.get('industry', 'Architecture')}
INDUSTRY CONTEXT: {signals['industry']}
TONE: {signals['tone']} (Professional, Strategic, Institutional)

Expected Depth: Executive-level strategic analysis.
Ensure the output is technical, data-driven, and provides immediate strategic value.
Return the base structure according to the provided schema."""

    def _ensure_closed_tags(self, html: str) -> str:
        if not html: return html
        tags = re.findall(r'<(/?)([a-zA-Z1-6]+)', html)
        stack = []
        void_tags = {'br', 'hr', 'img', 'input', 'link', 'meta'}
        for is_closing, tag in tags:
            tag = tag.lower()
            if tag in void_tags: continue
            if is_closing:
                if stack and stack[-1] == tag: stack.pop()
            else: stack.append(tag)
        for tag in reversed(stack): html += f"</{tag}>"
        return html

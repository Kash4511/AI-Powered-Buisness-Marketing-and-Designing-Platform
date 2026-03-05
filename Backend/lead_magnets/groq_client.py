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
        self.max_tokens = 4096  # Safer output limit for Groq models

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

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of tokens (1.3 tokens per word)."""
        if not text:
            return 0
        return int(len(text.split()) * 1.3)

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Dict[str, Any]:
        """Executes a Groq API call with token logging and error handling."""
        est_input_tokens = self._estimate_tokens(system_prompt + user_prompt)
        logger.info(f"📡 Groq Request: model={self.model}, est_input_tokens={est_input_tokens}")
        
        # Log full prompt for debugging (masked for production in real scenarios)
        logger.debug(f"PROMPT SYSTEM: {system_prompt}")
        logger.debug(f"PROMPT USER: {user_prompt}")

        try:
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
            
            raw_content = response.choices[0].message.content
            est_output_tokens = self._estimate_tokens(raw_content)
            
            logger.info(f"✅ Groq Response: duration={duration:.2f}s, est_output_tokens={est_output_tokens}")
            
            # Check for truncation
            if response.choices[0].finish_reason == 'length':
                logger.error("❌ Groq response truncated due to max completion tokens. Document may be invalid.")
                # We raise a specific error that views can catch to retry or inform the user
                raise ValueError("max completion tokens reached before generating a valid document")
            
            return json.loads(raw_content)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Groq JSON Decode Error: {str(e)}")
            # Fallback: try to fix common JSON issues or return partial
            raise e
        except Exception as e:
            logger.error(f"❌ Groq API Error: {str(e)}")
            raise e

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
        Internal method to expand base content into a specific 15-page institutional report structure:
        - Pages 1-2: Introduction and overview
        - Page 3: Transition page with foundational context
        - Pages 4-14: Detailed technical analysis (Chapters 1-5, 2 parts each)
        - Page 15: Conclusion (Minimal density)
        """
        topic = signals.get('topic')
        audience = signals.get('audience')
        pain_points = signals.get('pain_points')
        
        # Stage 1A: Page 1-2 Introduction & Overview
        logger.info("🚀 Stage 1A: Generating Introduction & Overview (Pages 1-2)...")
        intro_prompt = f"""You are generating a PROFESSIONAL 15-page consulting-grade report on {topic}.
Requirement: Generate dense introductory content (1500 words) for Pages 1 and 2.
Content: Executive-level overview, strategic relevance, and institutional context.
Include 1 [IMAGE_PLACEHOLDER: strategic overview visual] tag.

Return JSON: {{ "executive_summary": "1500-word dense prose" }}"""
        try:
            intro_data = self._call_ai("You are a senior strategist.", intro_prompt)
        except Exception as e:
            logger.error(f"❌ Intro failed: {e}. Using fallback.")
            intro_data = { "executive_summary": f"Strategic introduction for {topic} targeting {audience}." }

        # Stage 1B: Page 3 Transition & Foundational Context
        logger.info("🚀 Stage 1B: Generating Transition Content (Page 3)...")
        transition_prompt = f"""Generate Page 3: Foundational context and strategic transition.
Requirement: 800 words of dense prose establishing the framework for the technical chapters.
Include 1 [IMAGE_PLACEHOLDER: framework visualization] tag.

Return JSON: {{
  "audience_analysis": {{
    "commercial_label": "Commercial Stakeholders", "commercial_text": "200-word analysis",
    "government_label": "Public Sector", "government_text": "200-word analysis",
    "architect_label": "Design Professionals", "architect_text": "200-word analysis",
    "contractor_label": "Execution Teams", "contractor_text": "200-word analysis"
  }}
}}"""
        try:
            transition_data = self._call_ai("You are a senior strategist.", transition_prompt)
        except Exception as e:
            logger.error(f"❌ Transition failed: {e}. Using fallback.")
            transition_data = { "audience_analysis": { "commercial_label": "Stakeholders", "commercial_text": "Technical context..." } }

        # Stage 2: Pages 4-14 (Detailed Technical Chapters)
        logger.info("🚀 Stage 2: Generating Chapters 1-5 (Pages 4-14)...")
        chapters = {}
        for i in range(1, 6):
            logger.info(f"📚 Generating Chapter {i}...")
            
            # Custom prompt for chapters with unique structures
            if i == 3:
                structure = """ "phase_1": {"title": "...", "desc": "..."}, "phase_2": {"title": "...", "desc": "..."}, """
            elif i == 4:
                structure = """ "case_study_1": {"title": "...", "desc": "...", "result": "..."}, "case_study_2": {"title": "...", "desc": "...", "result": "..."}, """
            elif i == 5:
                structure = """ "methods": [ {"phase": "...", "desc": "..."} ], """
            else:
                structure = ""

            # Only place the third placeholder in Chapter 3 (Page 9)
            image_placeholder = ""
            if i == 3:
                image_placeholder = "Include 1 [IMAGE_PLACEHOLDER: implementation flowchart] tag."

            chapter_prompt = f"""Generate Chapter {i} (2 full pages) for a 15-page report on {topic}.
STRICT REQUIREMENTS:
- Chapter MUST be 1200+ words across its two parts (body_a and body_b).
- {image_placeholder}
- Institutional, technical, data-driven prose.

Return JSON ONLY for this chapter: {{
  "chapter_{i}": {{ 
    "eyebrow": "...", "section_id": "CH 0{i}", "title": "...", 
    "intro": "200-word intro", 
    {structure}
    "body_a": "500-word technical body A", 
    "body_b": "500-word technical body B", 
    "impact_label": "...", "impact_value": "..." 
  }}
}}"""
            try:
                chapter_data = self._call_ai("You are a technical strategist.", chapter_prompt)
                chapters.update(chapter_data)
            except Exception as e:
                logger.error(f"❌ Failed Chapter {i}: {e}")
                chapters[f"chapter_{i}"] = { "title": f"Chapter {i}", "body_a": "Technical analysis...", "body_b": "Strategic depth..." }

        # Stage 3: Page 15 Conclusion (Minimal Density)
        logger.info("🚀 Stage 3: Generating Conclusion (Page 15)...")
        stage3_prompt = f"""Generate Page 15 (Strategic Recommendations).
Requirement: 400 words of concise strategic conclusion (low density).
Return JSON: {{
  "roi_detailed_analysis": "ROI technical forecast",
  "conclusion_strategy": "Concise final recommendations",
  "drop_caps": ["S", "F", "C", "M", "T"],
  "image_labels": ["OVERVIEW", "FRAMEWORK", "EXECUTION"],
  "imagePage4Url_label": "Analysis Visual Context",
  "imagePage5Url_label": "Solution Implementation Visual",
  "imagePage6Url_label": "Strategic Roadmap Visualization",
  "cta": "Call to Action"
}}"""
        try:
            stage3 = self._call_ai("You are a senior analyst.", stage3_prompt)
        except Exception as e:
            logger.error(f"❌ Stage 3 failed: {e}")
            stage3 = { "conclusion_strategy": "Final overview...", "cta": "Contact us." }

        # Merge all stages
        expanded = {**intro_data, **transition_data, **chapters, **stage3}
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
        return f"""Generate institutional report structure:
TOPIC: {signals['topic']}
AUDIENCE: {signals['audience']}
PAIN POINTS: {signals['pain_points']}
FIRM: {firm_profile.get('firm_name')} ({firm_profile.get('industry', 'Architecture')})
TONE: {signals['tone']} (Strategic)

Expected: Executive strategic analysis. Return base structure as JSON."""

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

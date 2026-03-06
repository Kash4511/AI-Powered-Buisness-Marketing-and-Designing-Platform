import os
import json
import logging
import time
import re
from typing import Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSAL 8-SECTION STRUCTURE
# All document types use the same 8 sections — each generated individually
# with a domain-expert prompt that forces topic-specific, non-generic content.
# ─────────────────────────────────────────────────────────────────────────────

SECTIONS = [
    (
        "executive_summary",
        "Executive Summary",
        "OVERVIEW",
        (
            "Write the Executive Summary for this guide on {topic}.\n"
            "Explain: what {topic} is, why it matters RIGHT NOW for {audience}, "
            "and what specific pain points ({pain_points}) this guide addresses.\n"
            "Include real statistics or data points specific to {topic}.\n"
            "End with a clear statement of what the reader will gain from this guide.\n"
            "300-400 words. Be specific to {topic} — not generic project management advice."
        )
    ),
    (
        "key_challenges",
        "Understanding the Key Challenges",
        "CHALLENGES",
        (
            "Write the Key Challenges section for {audience} working in {topic}.\n"
            "For EACH pain point in [{pain_points}], write a dedicated subsection with:\n"
            "  - Why this specific challenge occurs in {topic} (root cause)\n"
            "  - How it concretely impacts {audience} (financial, operational, social impact)\n"
            "  - A real-world example or scenario from {topic} practice\n"
            "These must be challenges SPECIFIC to {topic} — not generic business challenges.\n"
            "350-450 words total."
        )
    ),
    (
        "strategic_framework",
        "Strategic Framework",
        "FRAMEWORK",
        (
            "Write a Strategic Framework for solving {topic} challenges for {audience}.\n"
            "Create a NAMED framework (e.g. a 4-step or 5-step process) specific to {topic}.\n"
            "Each step must:\n"
            "  - Have a descriptive name tied to {topic} vocabulary\n"
            "  - Explain what actually happens in this step (not generic advice)\n"
            "  - Reference at least one of these pain points: {pain_points}\n"
            "Include a real example of how this framework applies to {topic}.\n"
            "Do NOT use steps like 'Define Goals' or 'Identify Stakeholders' — those are generic PM.\n"
            "350-450 words."
        )
    ),
    (
        "implementation_strategy",
        "Implementation Strategy",
        "IMPLEMENTATION",
        (
            "Write an Implementation Strategy section for {audience} applying {topic} in practice.\n"
            "Include:\n"
            "  - Specific processes unique to {topic} (not generic project phases)\n"
            "  - Decision points that {audience} will actually face in {topic} work\n"
            "  - Tools, methods, or approaches used by practitioners in {topic}\n"
            "  - Common implementation mistakes specific to {topic} and how to avoid them\n"
            "Reference how {pain_points} affect implementation and how to navigate them.\n"
            "350-450 words."
        )
    ),
    (
        "risk_management",
        "Risk Management",
        "RISK",
        (
            "Write a Risk Management section for {audience} working on {topic}.\n"
            "Identify 5-6 risks that are SPECIFIC to {topic} — not generic project risks.\n"
            "For each risk include: what causes it in {topic}, how it impacts {audience}, "
            "and a concrete mitigation strategy used in real {topic} practice.\n"
            "Format as: <h3>Risk Name</h3> then explanation paragraph for each risk.\n"
            "Connect risks back to these pain points: {pain_points}.\n"
            "350-450 words."
        )
    ),
    (
        "best_practices",
        "Best Practices & Emerging Approaches",
        "BEST PRACTICE",
        (
            "Write a Best Practices section covering modern methods and tools for {topic}.\n"
            "Include:\n"
            "  - 4-5 best practices that expert practitioners use in {topic}\n"
            "  - Specific tools, technologies, or methodologies relevant to {topic}\n"
            "  - Examples of how leading {audience} apply these in real {topic} projects\n"
            "  - Emerging trends or innovations changing how {topic} is practiced\n"
            "These must be DOMAIN-SPECIFIC to {topic} — not generic advice.\n"
            "Avoid vague phrases. Explain HOW things actually work.\n"
            "350-450 words."
        )
    ),
    (
        "action_checklist",
        "Practical Action Checklist",
        "CHECKLIST",
        (
            "Write a Practical Action Checklist for {audience} working on {topic}.\n"
            "Provide 15-20 specific, actionable checklist items.\n"
            "Each item must be:\n"
            "  - Specific to {topic} — not generic business advice\n"
            "  - Something {audience} can DO immediately or in the next 30 days\n"
            "  - Connected to resolving one of these pain points: {pain_points}\n"
            "Format as a <ul> list with each item in <li> tags.\n"
            "Group items under subheadings by phase or theme if helpful.\n"
            "300-400 words."
        )
    ),
    (
        "conclusion",
        "Conclusion & Next Steps",
        "CONCLUSION",
        (
            "Write the Conclusion and Next Steps for this {topic} guide for {audience}.\n"
            "Include:\n"
            "  - A brief synthesis of the most important insights from this guide\n"
            "  - 3 immediate next steps {audience} should take (specific to {topic})\n"
            "  - A 90-day action agenda specific to {topic} practice\n"
            "  - A compelling closing statement about why {topic} matters for {audience}\n"
            "Do NOT just summarize the sections — add forward-looking guidance.\n"
            "250-350 words."
        )
    ),
]

# Map doc_type → display label (kept for TOC and cover page)
DOC_TYPE_LABELS = {
    "guide":           "Strategic Guide",
    "case_study":      "Case Study Report",
    "checklist":       "Implementation Checklist",
    "roi_calculator":  "ROI Analysis Report",
    "trends_report":   "Industry Trends Report",
    "design_portfolio":"Design Portfolio",
    "client_onboarding":"Client Onboarding Guide",
    "custom":          "Strategic Report",
}

_TYPE_MAP = {
    "guide":                   "guide",
    "strategic guide":         "guide",
    "case_study":              "case_study",
    "case study":              "case_study",
    "checklist":               "checklist",
    "roi_calculator":          "roi_calculator",
    "roi calculator":          "roi_calculator",
    "trends_report":           "trends_report",
    "trends report":           "trends_report",
    "design_portfolio":        "design_portfolio",
    "design portfolio":        "design_portfolio",
    "client_onboarding_flow":  "client_onboarding",
    "client_onboarding":       "client_onboarding",
    "client onboarding flow":  "client_onboarding",
    "custom":                  "custom",
}

# Allowed HTML tags — anything else gets stripped from Groq output
ALLOWED_TAGS = {"p", "strong", "em", "h3", "h4", "ul", "ol", "li", "br"}


class GroqClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")
        self.client      = Groq(api_key=api_key)
        self.model       = "llama-3.1-8b-instant"  # swap to llama-3.3-70b-versatile for production
        self.temperature = 0.45
        self.max_tokens  = 4096

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, Any]:
        raw_type    = str(
            user_answers.get("document_type")
            or user_answers.get("lead_magnet_type")
            or "guide"
        ).lower().strip()
        doc_type    = _TYPE_MAP.get(raw_type, "guide")
        pain_points = user_answers.get("pain_points", [])
        audience    = user_answers.get("target_audience", "Stakeholders")

        return {
            "topic":           user_answers.get("main_topic", "Strategic Design"),
            "audience":        ", ".join(audience) if isinstance(audience, list) else str(audience),
            "pain_points":     ", ".join(pain_points) if isinstance(pain_points, list) else str(pain_points),
            "desired_outcome": user_answers.get("desired_outcome", ""),
            "cta":             user_answers.get("call_to_action", ""),
            "special":         user_answers.get("special_requests", ""),
            "tone":            user_answers.get("tone", "Professional"),
            "industry":        user_answers.get("industry", ""),
            "document_type":   doc_type,
        }

    def generate_lead_magnet_json(self, signals: Dict[str, Any], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        doc_type    = signals.get("document_type", "guide")
        type_label  = DOC_TYPE_LABELS.get(doc_type, "Strategic Guide")

        logger.info(f"📄 Generating {type_label} | topic={signals['topic']} | model={self.model}")

        # Step 1 — Generate title
        title_data = self._generate_title(signals, type_label)

        # Step 2 — Generate each section individually (8 calls)
        # One section per call = topic-specific depth, no token overflow
        expansions: Dict[str, str] = {}
        for key, title, label, brief in SECTIONS:
            logger.info(f"✍️  Generating section: {key}")
            expansions[key] = self._generate_section(
                key=key, title=title, brief=brief, signals=signals
            )

        return {
            "title":                   title_data.get("title", signals["topic"]),
            "subtitle":                title_data.get("subtitle", type_label),
            "target_audience_summary": title_data.get("target_audience_summary", ""),
            "document_type":           doc_type,
            "document_type_label":     type_label,
            "expansions":              expansions,
        }

    def normalize_ai_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        exp = raw.get("expansions", {})

        normalized: Dict[str, Any] = {
            "title":               raw.get("title", "Strategic Report"),
            "subtitle":            raw.get("subtitle", ""),
            "summary":             raw.get("target_audience_summary", ""),
            "document_type":       raw.get("document_type", "guide"),
            "document_type_label": raw.get("document_type_label", "Strategic Guide"),
            "sections_config":     SECTIONS,
        }

        for key, _title, _label, _ in SECTIONS:
            content = exp.get(key, "")
            if isinstance(content, dict):
                content = json.dumps(content)
            content = content if isinstance(content, str) else str(content)
            # Sanitize: strip any disallowed tags that Groq sneaked in
            normalized[key] = self._sanitize_html(content)

        return normalized

    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Dict[str, Any],
        signals: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        content_sections: List[Dict] = []
        toc_sections:     List[Dict] = []

        for idx, (key, title, label, _) in enumerate(SECTIONS):
            page_num = f"{idx + 3:02d}"
            content  = ai_content.get(key, "")
            content_sections.append({
                "key":      key,
                "title":    title,
                "label":    label,
                "page_num": page_num,
                "content":  content,
            })
            toc_sections.append({
                "title":    title,
                "label":    label,
                "page_num": page_num,
            })

        primary_color = (
            firm_profile.get("primary_brand_color")
            or (signals or {}).get("primary_color")
            or "#2a5766"
        )
        if primary_color and not str(primary_color).startswith("#"):
            primary_color = "#" + primary_color

        return {
            "mainTitle":         ai_content.get("title"),
            "documentSubtitle":  ai_content.get("subtitle"),
            "documentTypeLabel": ai_content.get("document_type_label", "Strategic Guide"),
            "companyName":       firm_profile.get("firm_name", ""),
            "emailAddress":      firm_profile.get("work_email", ""),
            "phoneNumber":       firm_profile.get("phone_number", ""),
            "website":           firm_profile.get("firm_website", ""),
            "footerText":        f"© {firm_profile.get('firm_name', 'Strategic Report')}",
            "primaryColor":      primary_color,
            "secondaryColor":    firm_profile.get("secondary_brand_color") or "#FFFFFF",
            "tertiaryColor":     firm_profile.get("tertiary_brand_color") or "#4F7A8B",
            "accentColor":       firm_profile.get("accent_color") or "#E8F1F4",
            "creamColor":        firm_profile.get("cream_color") or "#F7F4EF",
            "creamDarkColor":    firm_profile.get("cream_dark_color") or "#EBE6DA",
            "inkColor":          firm_profile.get("ink_color") or "#1A1A1A",
            "inkMidColor":       firm_profile.get("ink_mid_color") or "#444444",
            "inkLightColor":     firm_profile.get("ink_light_color") or "#888888",
            "ruleColor":         firm_profile.get("rule_color") or "#DDDDDD",
            "ruleLightColor":    firm_profile.get("rule_light_color") or "#EEEEEE",
            "coverTextColor":    firm_profile.get("cover_text_color") or "#FFFFFF",
            "coverLogoFilter":   firm_profile.get("cover_logo_filter") or "brightness(0) invert(1)",
            "summary":           ai_content.get("summary", ""),
            "content_sections":  content_sections,
            "toc_sections":      toc_sections,
            "image_1_url":       firm_profile.get("image_1_url", ""),
            "image_2_url":       firm_profile.get("image_2_url", ""),
            "image_3_url":       firm_profile.get("image_3_url", ""),
            "image_1_caption":   firm_profile.get("image_1_caption", "Strategic Context"),
            "image_2_caption":   firm_profile.get("image_2_caption", "Technical Framework"),
            "image_3_caption":   firm_profile.get("image_3_caption", "Implementation Overview"),
            "cta":               ai_content.get("conclusion", "Contact us to implement this framework."),
        }

    def ensure_section_content(self, sections, signals, firm_profile):
        """Legacy compatibility."""
        return sections or []

    # ── PRIVATE ───────────────────────────────────────────────────────────────

    def _generate_title(self, signals: Dict, type_label: str) -> Dict:
        system = (
            "You are a senior document strategist. "
            "Return valid JSON only. No markdown fences."
        )
        prompt = (
            f"Generate a title package for a {type_label} guide.\n\n"
            f"Topic: {signals['topic']}\n"
            f"Audience: {signals['audience']}\n"
            f"Pain Points: {signals['pain_points']}\n\n"
            f"Rules:\n"
            f"- Title: 3-7 words, specific to the topic. No generic words like 'Ultimate' or 'Complete'.\n"
            f"- Subtitle: 10-16 words describing the specific value delivered to the audience.\n"
            f"- Summary: One sentence — who this is for and what outcome they get.\n\n"
            f'Return ONLY: {{"title": "...", "subtitle": "...", "target_audience_summary": "..."}}'
        )
        logger.info(f"🔵 Generating title | topic={signals['topic']}")
        return self._call_ai(system, prompt, max_tokens=300)

    def _generate_section(self, key: str, title: str, brief: str, signals: Dict) -> str:
        """
        Generates one section at a time.
        Uses a domain-expert forcing prompt that demands topic-specific content.
        Raises immediately on failure — no silent fallbacks.
        """
        brief_filled = brief.format(
            topic       = signals["topic"],
            audience    = signals["audience"],
            pain_points = signals["pain_points"],
            industry    = signals.get("industry", signals["topic"]),
        )

        system = (
            f"You are an expert consultant and domain specialist in {signals['topic']}.\n"
            f"You are writing one section of a professional lead-magnet guide.\n\n"
            f"ABSOLUTE RULES:\n"
            f"1. Every sentence must be SPECIFIC to {signals['topic']} — not generic business advice.\n"
            f"2. Address these pain points directly: {signals['pain_points']}\n"
            f"3. Write for this audience: {signals['audience']}\n"
            f"4. BANNED phrases: 'leverage synergies', 'optimize solutions', 'unlock value', "
            f"'drive innovation', 'best practices' (use specific examples instead)\n"
            f"5. Use HTML: <p> paragraphs, <strong> key terms, <h3> subheadings, <ul>/<li> lists\n"
            f"6. DO NOT include the section title — it is already rendered above your content\n"
            f"7. Start with a <p> tag, not <h3>\n"
            f"8. Return valid JSON only. No markdown fences.\n"
        )

        prompt = (
            f"Write the '{title}' section of this {signals['topic']} guide.\n\n"
            f"SECTION BRIEF:\n{brief_filled}\n\n"
            f"SPECIAL REQUESTS: {signals.get('special', 'None')}\n\n"
            f'Return ONLY: {{"{key}": "<p>your content here</p>"}}'
        )

        logger.info(f"🔵 Section '{key}' | topic={signals['topic']}")
        raw = self._call_ai(system, prompt, max_tokens=2500)

        content = self._extract_content(raw, key)
        word_count = len(content.split()) if content else 0

        logger.info(f"✅ Section '{key}': {word_count} words")

        if word_count < 20:
            raise ValueError(
                f"Section '{key}' returned only {word_count} words. "
                f"Groq response keys: {list(raw.keys())}. "
                f"Raw snippet: {str(raw)[:400]}"
            )

        return self._sanitize_html(content)

    def _extract_content(self, result: Dict, key: str) -> str:
        """
        Robustly pull section content from whatever JSON shape Groq returned.
        Priority: exact key → 'content' key → first long string value.
        Logs exactly what it found so failures are visible immediately.
        """
        if not result:
            logger.error(f"❌ _extract_content: empty result for key='{key}'")
            return ""
        if key in result and isinstance(result[key], str) and len(result[key]) > 30:
            return result[key]
        if "content" in result and isinstance(result["content"], str) and len(result["content"]) > 30:
            logger.warning(f"⚠️ key='{key}' missing — used 'content' key")
            return result["content"]
        for k, v in result.items():
            if isinstance(v, str) and len(v) > 80:
                logger.warning(f"⚠️ key='{key}' missing — used first long string under '{k}'")
                return v
        logger.error(
            f"❌ _extract_content FAILED for '{key}'. "
            f"Keys: {list(result.keys())}. "
            f"Preview: { {k: str(v)[:60] for k, v in result.items()} }"
        )
        return ""

    def _sanitize_html(self, html: str) -> str:
        """
        Strip any HTML tags not in ALLOWED_TAGS.
        Also removes raw [IMAGE_PLACEHOLDER: ...] markers Groq sometimes injects.
        Ensures all tags are properly closed.
        """
        if not html:
            return html

        # Remove image placeholders
        html = re.sub(r'\[IMAGE_PLACEHOLDER:[^\]]*\]', '', html)

        # Strip disallowed tags (keep their inner text)
        def replace_tag(m):
            tag = m.group(1).lower().split()[0] if m.group(1) else ""
            if tag in ALLOWED_TAGS:
                return m.group(0)
            return ""  # strip the tag, keep content between tags via separate pass

        html = re.sub(r'<(/?)(\w[\w\s="\'.-]*?)>', lambda m: (
            m.group(0) if m.group(2).split()[0].lower() in ALLOWED_TAGS else ""
        ), html)

        # Close any unclosed tags
        html = self._ensure_closed_tags(html)

        return html.strip()

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Dict:
        start  = time.time()
        tokens = max_tokens or self.max_tokens

        logger.info(f"🔵 Groq call | model={self.model} | max_tokens={tokens}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=tokens,
                response_format={"type": "json_object"},
            )
        except Exception as api_err:
            import traceback as _tb
            logger.error(f"❌ Groq API FAILED: {type(api_err).__name__}: {api_err}\n{_tb.format_exc()}")
            raise RuntimeError(f"Groq API call failed: {type(api_err).__name__}: {api_err}") from api_err

        duration = time.time() - start
        finish   = response.choices[0].finish_reason
        raw_text = response.choices[0].message.content or ""

        logger.info(f"🟢 Groq | {duration:.2f}s | finish={finish} | chars={len(raw_text)}")

        if finish == "length":
            logger.error(
                f"❌ Groq TRUNCATED (finish=length). max_tokens={tokens} too low. "
                f"Snippet: {raw_text[:300]}"
            )
            raise ValueError(
                f"Groq truncated response (finish_reason=length). "
                f"Increase max_tokens above {tokens}. Raw: {raw_text[:200]}"
            )

        if not raw_text.strip():
            raise ValueError(f"Groq returned empty response. finish_reason={finish}")

        try:
            parsed = json.loads(raw_text)
            logger.info(f"✅ JSON parsed | keys={list(parsed.keys())}")
            return parsed
        except json.JSONDecodeError as je:
            logger.error(f"❌ JSON PARSE FAILED: {je}\nFull raw:\n{raw_text}")
            raise ValueError(f"Groq returned invalid JSON: {je}. Raw: {raw_text[:400]}") from je

    def _ensure_closed_tags(self, html: str) -> str:
        if not html:
            return html
        void_tags = {"br", "hr", "img", "input", "link", "meta"}
        tags  = re.findall(r"<(/?)([a-zA-Z1-6]+)", html)
        stack: List[str] = []
        for is_closing, tag in tags:
            tag = tag.lower()
            if tag in void_tags:
                continue
            if is_closing:
                if stack and stack[-1] == tag:
                    stack.pop()
            else:
                stack.append(tag)
        for tag in reversed(stack):
            html += f"</{tag}>"
        return html
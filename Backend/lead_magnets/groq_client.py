import os
import json
import logging
import time
import re
from typing import Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 8 SECTIONS — each has a laser-focused brief that forces domain depth
# Token budget per section: ~1,800 tokens → 8 sections = ~14,400 total
# ─────────────────────────────────────────────────────────────────────────────
SECTIONS = [
    (
        "executive_summary",
        "Executive Summary",
        "OVERVIEW",
        (
            "Write the Executive Summary for a professional guide on {topic} for {audience}.\n"
            "REQUIRED elements (all must appear):\n"
            "1. One crisp paragraph explaining what {topic} is in the context of {audience} work — "
            "not a dictionary definition, but why it matters operationally.\n"
            "2. A paragraph explaining the current landscape: what is changing in {topic} right now "
            "and why {audience} cannot afford to ignore it.\n"
            "3. For EACH pain point in [{pain_points}]: one sentence stating the specific consequence "
            "of this pain point for {audience} in {topic} work (e.g. cost overrun, missed deadline, "
            "community backlash, regulatory rejection).\n"
            "4. A closing paragraph: what this guide delivers and the tangible outcome the reader gets.\n"
            "150-200 words. Dense, specific, no filler."
        )
    ),
    (
        "key_challenges",
        "Key Challenges",
        "CHALLENGES",
        (
            "Write the Key Challenges section for {audience} in {topic}.\n"
            "For EACH pain point in [{pain_points}] write a named <h3> subsection containing:\n"
            "- Root cause: WHY does this specific challenge occur in {topic}? "
            "(be mechanistic — e.g. fragmented land ownership, multi-agency approval chains, "
            "community trust deficits — not 'lack of alignment')\n"
            "- Impact: concrete operational or financial consequence for {audience} "
            "(e.g. '6-month delays', '$200k redesign costs', 'loss of community buy-in')\n"
            "- Real scenario: 2-3 sentences describing a realistic situation where this plays out\n"
            "Every subsection must be grounded in {topic} specifically.\n"
            "180-220 words total."
        )
    ),
    (
        "strategic_framework",
        "Strategic Framework",
        "FRAMEWORK",
        (
            "Write a Strategic Framework section for {topic} for {audience}.\n"
            "Invent a NAMED framework (3-5 steps) that is genuinely specific to {topic}.\n"
            "RULES:\n"
            "- Step names must use vocabulary from {topic} domain "
            "(e.g. for urban placemaking: 'Community Pulse Mapping', 'Activation Sequencing')\n"
            "- Each step: name + 2-3 sentences on what practitioners actually DO in this step\n"
            "- At least 2 steps must directly address pain points from: {pain_points}\n"
            "- Include one concrete example of the framework applied to a real-world {topic} scenario\n"
            "- DO NOT use generic steps like 'Define Goals', 'Plan', 'Execute', 'Review'\n"
            "180-220 words."
        )
    ),
    (
        "implementation_strategy",
        "Implementation Strategy",
        "IMPLEMENTATION",
        (
            "Write an Implementation Strategy for {audience} applying {topic}.\n"
            "Structure as THREE phases with specific {topic}-domain actions in each:\n"
            "Phase 1 (weeks 1-4): discovery/diagnosis actions unique to {topic}\n"
            "Phase 2 (weeks 5-12): design/coordination actions unique to {topic}\n"
            "Phase 3 (weeks 13+): delivery/activation actions unique to {topic}\n"
            "For each phase include:\n"
            "- 2-3 specific tasks practitioners do in {topic} (not 'hold meetings')\n"
            "- One decision point {audience} will face and how to navigate it\n"
            "- How one pain point from [{pain_points}] surfaces in this phase and what to do\n"
            "180-220 words."
        )
    ),
    (
        "risk_management",
        "Risk Management",
        "RISK",
        (
            "Write a Risk Management section for {audience} working on {topic}.\n"
            "Identify exactly 4 risks SPECIFIC to {topic} — not 'scope creep' or 'budget overrun'.\n"
            "For each risk use this structure:\n"
            "<h3>[Risk Name specific to {topic}]</h3>\n"
            "<p><strong>Cause:</strong> [what triggers this in {topic} work]</p>\n"
            "<p><strong>Impact on {audience}:</strong> [specific consequence]</p>\n"
            "<p><strong>Mitigation:</strong> [what expert practitioners actually do]</p>\n"
            "At least 2 risks must be directly caused by pain points in [{pain_points}].\n"
            "180-220 words."
        )
    ),
    (
        "best_practices",
        "Best Practices",
        "METHODS",
        (
            "Write a Best Practices section for {audience} in {topic}.\n"
            "Provide exactly 4 best practices. Each must:\n"
            "- Have a specific name (not 'Communicate Well' or 'Plan Ahead')\n"
            "- Explain the METHOD: how expert {audience} actually implement this in {topic}\n"
            "- Give one concrete example from {topic} practice\n"
            "- Reference how it addresses one of [{pain_points}]\n"
            "Examples of what good looks like for urban placemaking: "
            "'Tactical Urbanism Pilots', 'Community Asset Mapping', 'Pop-up Activation Testing'\n"
            "Match this specificity for {topic}.\n"
            "180-220 words."
        )
    ),
    (
        "action_checklist",
        "Action Checklist",
        "CHECKLIST",
        (
            "Write a practical Action Checklist for {audience} working on {topic}.\n"
            "Create exactly 3 groups of checklist items:\n"
            "Group 1 — <h3>Before You Start</h3>: 4-5 items specific to {topic} preparation\n"
            "Group 2 — <h3>During Implementation</h3>: 4-5 items specific to {topic} execution\n"
            "Group 3 — <h3>Measuring Success</h3>: 4-5 items with {topic}-specific KPIs/metrics\n"
            "Each item must be a concrete action, not a vague instruction.\n"
            "Bad: 'Engage stakeholders'. Good: 'Map all landowners within 500m of the site'\n"
            "Bad: 'Track progress'. Good: 'Measure footfall change weekly using manual counts'\n"
            "Every item must be specific to {topic} and {audience}.\n"
            "150-180 words."
        )
    ),
    (
        "conclusion",
        "Conclusion & Next Steps",
        "CONCLUSION",
        (
            "Write the Conclusion & Next Steps for this {topic} guide for {audience}.\n"
            "Structure:\n"
            "1. One paragraph: the single most important insight from this guide specific to {topic}\n"
            "2. Three numbered next steps — each must be a specific action in {topic} "
            "(not 'read more' or 'consult an expert')\n"
            "3. One forward-looking paragraph: what {audience} who master {topic} will achieve "
            "in the next 2-3 years, tied to resolving [{pain_points}]\n"
            "4. One closing sentence that is a direct call to action.\n"
            "130-160 words. Punchy, specific, no filler."
        )
    ),
]

DOC_TYPE_LABELS = {
    "guide":            "Strategic Guide",
    "case_study":       "Case Study Report",
    "checklist":        "Implementation Checklist",
    "roi_calculator":   "ROI Analysis Report",
    "trends_report":    "Industry Trends Report",
    "design_portfolio": "Design Portfolio",
    "client_onboarding":"Client Onboarding Guide",
    "custom":           "Strategic Report",
}

_TYPE_MAP = {
    "guide":                  "guide",
    "strategic guide":        "guide",
    "case_study":             "case_study",
    "case study":             "case_study",
    "checklist":              "checklist",
    "roi_calculator":         "roi_calculator",
    "roi calculator":         "roi_calculator",
    "trends_report":          "trends_report",
    "trends report":          "trends_report",
    "design_portfolio":       "design_portfolio",
    "design portfolio":       "design_portfolio",
    "client_onboarding_flow": "client_onboarding",
    "client_onboarding":      "client_onboarding",
    "client onboarding flow": "client_onboarding",
    "custom":                 "custom",
}

ALLOWED_TAGS = {"p", "strong", "em", "h3", "h4", "ul", "ol", "li", "br"}


class GroqClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")
        self.client      = Groq(api_key=api_key)
        self.model       = "llama-3.1-8b-instant"   # swap to llama-3.3-70b-versatile for production
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
        doc_type   = signals.get("document_type", "guide")
        type_label = DOC_TYPE_LABELS.get(doc_type, "Strategic Guide")
        logger.info(f"📄 {type_label} | topic={signals['topic']} | model={self.model}")

        title_data = self._generate_title(signals, type_label)
        expansions: Dict[str, str] = {}
        for key, title, label, brief in SECTIONS:
            logger.info(f"✍️  {key}")
            expansions[key] = self._generate_section(key, title, brief, signals)

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
        for key, *_ in SECTIONS:
            content = exp.get(key, "")
            if isinstance(content, dict):
                content = json.dumps(content)
            normalized[key] = self._sanitize_html(
                content if isinstance(content, str) else str(content)
            )
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
            content_sections.append({
                "key": key, "title": title, "label": label,
                "page_num": page_num, "content": ai_content.get(key, ""),
            })
            toc_sections.append({"title": title, "label": label, "page_num": page_num})

        primary_color = (
            firm_profile.get("primary_brand_color")
            or (signals or {}).get("primary_color") or "#2a5766"
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
            "image_1_caption":   firm_profile.get("image_1_caption", "Field Context"),
            "image_2_caption":   firm_profile.get("image_2_caption", "Implementation"),
            "image_3_caption":   firm_profile.get("image_3_caption", "Outcomes"),
            "cta":               ai_content.get("conclusion", "Contact us to begin."),
        }

    def ensure_section_content(self, sections, signals, firm_profile):
        return sections or []

    # ── PRIVATE ───────────────────────────────────────────────────────────────

    def _generate_title(self, signals: Dict, type_label: str) -> Dict:
        system = "You are a senior document strategist. Return valid JSON only. No markdown."
        prompt = (
            f"Generate a title for a {type_label} on: {signals['topic']}\n"
            f"Audience: {signals['audience']}\n"
            f"Pain Points: {signals['pain_points']}\n\n"
            f"Rules: title = 3-7 words, domain-specific, no 'Ultimate'/'Complete'.\n"
            f"subtitle = 10-15 words, specific value delivered.\n"
            f"target_audience_summary = one sentence who this is for + outcome.\n"
            f'Return ONLY: {{"title":"...","subtitle":"...","target_audience_summary":"..."}}'
        )
        logger.info(f"🔵 title | {signals['topic']}")
        return self._call_ai(system, prompt, max_tokens=250)

    def _generate_section(self, key: str, title: str, brief: str, signals: Dict) -> str:
        brief_filled = brief.format(
            topic       = signals["topic"],
            audience    = signals["audience"],
            pain_points = signals["pain_points"],
            industry    = signals.get("industry") or signals["topic"],
        )

        system = (
            f"You are a domain expert and senior consultant specialising in {signals['topic']}.\n"
            f"You are writing one section of a professional lead-magnet guide.\n\n"
            f"NON-NEGOTIABLE RULES:\n"
            f"1. EVERY sentence must be specific to '{signals['topic']}' — no generic advice.\n"
            f"2. Directly address these pain points: {signals['pain_points']}\n"
            f"3. Write FOR this audience: {signals['audience']}\n"
            f"4. BANNED phrases (instant fail): 'leverage', 'synergies', 'optimize solutions', "
            f"'unlock value', 'drive innovation', 'holistic approach', 'best-in-class'\n"
            f"5. HTML only: <p>, <strong>, <h3>, <h4>, <ul>, <li>. No <div>, no <span>, no <table>.\n"
            f"6. DO NOT write the section title — it renders above your content.\n"
            f"7. First element MUST be <p>, never <h3>.\n"
            f"8. Return valid JSON only. No markdown. No prose outside JSON.\n"
        )

        prompt = (
            f"Write the '{title}' section for a {signals['topic']} guide.\n\n"
            f"BRIEF (follow exactly):\n{brief_filled}\n\n"
            f"SPECIAL REQUESTS: {signals.get('special') or 'None'}\n\n"
            f"Return ONLY this JSON:\n"
            f'{{"{key}": "your full HTML content here"}}'
        )

        logger.info(f"🔵 section '{key}'")
        raw = self._call_ai(system, prompt, max_tokens=1800)
        content = self._extract_content(raw, key)
        words = len(content.split()) if content else 0
        logger.info(f"✅ '{key}': {words} words")

        if words < 50:
            raise ValueError(
                f"Section '{key}' too short ({words} words). "
                f"Keys returned: {list(raw.keys())}. Snippet: {str(raw)[:300]}"
            )
        return self._sanitize_html(content)

    def _extract_content(self, result: Dict, key: str) -> str:
        if not result:
            logger.error(f"❌ empty result for '{key}'")
            return ""
        if key in result and isinstance(result[key], str) and len(result[key]) > 30:
            return result[key]
        if "content" in result and isinstance(result["content"], str) and len(result["content"]) > 30:
            logger.warning(f"⚠️ '{key}' missing — used 'content'")
            return result["content"]
        for k, v in result.items():
            if isinstance(v, str) and len(v) > 80:
                logger.warning(f"⚠️ '{key}' missing — used '{k}'")
                return v
        logger.error(f"❌ extract FAILED '{key}' | keys={list(result.keys())}")
        return ""

    def _sanitize_html(self, html: str) -> str:
        if not html:
            return html
        html = re.sub(r'\[IMAGE_PLACEHOLDER:[^\]]*\]', '', html)
        html = re.sub(
            r'<(/?)(\w+)([^>]*)>',
            lambda m: m.group(0) if m.group(2).lower() in ALLOWED_TAGS else "",
            html
        )
        return self._ensure_closed_tags(html).strip()

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Dict:
        import traceback as _tb
        tokens = max_tokens or self.max_tokens
        logger.info(f"🔵 Groq | max_tokens={tokens}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=tokens,
                # NO response_format json_object — it rejects valid HTML inside JSON strings
            )
        except Exception as e:
            logger.error(f"❌ Groq API: {type(e).__name__}: {e}\n{_tb.format_exc()}")
            raise RuntimeError(f"Groq API failed: {type(e).__name__}: {e}") from e

        finish   = response.choices[0].finish_reason
        raw_text = response.choices[0].message.content or ""
        logger.info(f"🟢 finish={finish} | chars={len(raw_text)}")

        if finish == "length":
            raise ValueError(f"Groq truncated (finish=length, max_tokens={tokens}). Raw: {raw_text[:200]}")
        if not raw_text.strip():
            raise ValueError(f"Groq empty response. finish={finish}")

        # Strip markdown fences if Groq wrapped in ```json ... ```
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            logger.info(f"✅ parsed | keys={list(parsed.keys())}")
            return parsed
        except json.JSONDecodeError:
            pass

        # ── Repair: Groq returned {"key": <html> without quoting the value
        m_repair = re.search(r'\{"(\w+)"\s*:\s*([^"\{][\s\S]*?)\s*\}\s*$', cleaned)
        if m_repair:
            try:
                repaired = json.dumps({m_repair.group(1): m_repair.group(2).strip()})
                parsed = json.loads(repaired)
                logger.warning(f"⚠️ repaired unquoted value | keys={list(parsed.keys())}")
                return parsed
            except Exception:
                pass

        # ── Fallback: extract key name + grab everything after the colon as content
        m_key = re.search(r'"(\w+)"\s*:\s*', cleaned)
        if m_key:
            key_name = m_key.group(1)
            content_start = m_key.end()
            content_val = cleaned[content_start:].rstrip().rstrip("}")
            if content_val.strip():
                logger.warning(f"⚠️ extracted raw content for key='{key_name}'")
                return {key_name: content_val.strip()}

        logger.error(f"❌ JSON parse fully failed\nRaw:\n{raw_text}")
        raise ValueError(f"Invalid JSON from Groq. Raw: {raw_text[:300]}")

    def _ensure_closed_tags(self, html: str) -> str:
        void = {"br", "hr", "img", "input", "link", "meta"}
        tags = re.findall(r"<(/?)([a-zA-Z1-6]+)", html)
        stack: List[str] = []
        for closing, tag in tags:
            tag = tag.lower()
            if tag in void:
                continue
            if closing:
                if stack and stack[-1] == tag:
                    stack.pop()
            else:
                stack.append(tag)
        for tag in reversed(stack):
            html += f"</{tag}>"
        return html
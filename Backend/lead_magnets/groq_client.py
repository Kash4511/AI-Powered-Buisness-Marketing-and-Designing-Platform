import os
import json
import logging
import time
import re
import traceback as _tb
from typing import Dict, Any, List, Tuple
from groq import Groq
from .config_helper import get_config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
SECTIONS = [
    ("introduction",         "Introduction",               "OVERVIEW",    "text-only", ""),
    ("industry_challenges",  "Common Challenges",          "CHALLENGES",  "text-only", ""),
    ("core_principles",      "Key Principles",             "PRINCIPLES",  "text-only", ""),
    ("practical_strategies", "Practical Strategies",       "STRATEGIES",  "text-only", ""),
    ("risk_management",      "Managing Risks",             "RISK",        "text-only", ""),
    ("best_practices",       "Best Practices",             "TIPS",        "text-only", ""),
    ("key_statistics",       "Facts and Figures",          "DATA",        "text-only", ""),
    ("implementation_roadmap", "Implementation Roadmap",    "ROADMAP",     "text-only", ""),
    ("traditional_vs_modern", "Traditional vs Modern",      "COMPARISON", "text-only", ""),
    ("case_study",           "Real World Example",         "CASE STUDY",  "text-only", ""),
    ("expert_insights",      "Expert Insights",            "INSIGHTS",    "text-only", ""),
    ("conclusion",           "Ready to Start",             "NEXT STEPS", "text-only", ""),
]

DOC_TYPE_LABELS = {
    "guide":             "Strategic Guide",
    "case_study":        "Case Study Report",
    "checklist":         "Implementation Checklist",
    "roi_calculator":    "ROI Analysis Report",
    "trends_report":     "Industry Trends Report",
    "design_portfolio":  "Design Portfolio",
    "client_onboarding": "Client Onboarding Guide",
    "custom":            "Strategic Report",
}

_TYPE_MAP = {
    "guide": "guide", "strategic_guide": "guide",
    "case_study": "case_study", "checklist": "checklist",
    "roi_calculator": "roi_calculator", "trends_report": "trends_report",
    "design_portfolio": "design_portfolio", "client_onboarding": "client_onboarding",
    "client_onboarding_flow": "client_onboarding", "onboarding_flow": "client_onboarding",
    "custom": "custom",
    "Guide": "guide", "Strategic Guide": "guide", "Case Study": "case_study",
    "Checklist": "checklist", "ROI Calculator": "roi_calculator",
    "Trends Report": "trends_report", "Design Portfolio": "design_portfolio",
    "Client Onboarding Flow": "client_onboarding", "Client Onboarding": "client_onboarding",
    "Custom": "custom",
}

ALLOWED_TAGS = {"p", "strong", "em", "h3", "h4", "ul", "ol", "li", "br", "blockquote"}

SECTION_KEYS = [s[0] for s in SECTIONS]


def _clean_topic_slug(topic: str) -> str:
    if not topic:
        return topic
    return " ".join(w.capitalize() for w in topic.replace("-", " ").replace("_", " ").split())


def _clean_company_name(name: str, email: str = "") -> str:
    if not name:
        return name
    is_username = (
        " " not in name.strip()
        and (name == name.lower() or re.search(r'\d', name))
        and "@" not in name
    )
    if not is_username:
        return name
    if email and "@" in email:
        domain = email.split("@")[-1].split(".")[0]
        if domain.lower() not in ("gmail", "yahoo", "hotmail", "outlook", "icloud", "me", "mac"):
            return domain.replace("-", " ").replace("_", " ").title()
    cleaned = re.sub(r'\d+$', '', name)
    return cleaned.title() if cleaned else name


def _strip_filler(html: str) -> str:
    if not html:
        return html
    filler_patterns = [
        r"this (section|guide|document|report) (provides?|offers?|explores?|covers?)",
        r"in (today's|the current|this) (fast[- ]paced|rapidly changing|evolving|dynamic|competitive|modern)",
        r"(as we|let us|let's|we will) (explore|delve|dive|look at|examine|discuss|uncover)",
        r"(the following|below) (section|content|information) (will|provides?|outlines?)",
        r"this comprehensive (guide|report|document|analysis)",
        r"furthermore,? (the|this|we)",
        r"additionally,? (the|this|we)",
        r"moreover,? (the|this|we)",
        r"first and foremost,?",
        r"welcome to (this|our)",
        r"(in this|this) (guide|section|document|report) (you will|we will|you'll|we'll)",
        r"whether you('re| are) (a|an|the)",
    ]
    filler_re = re.compile("|".join(filler_patterns), re.IGNORECASE)
    sentences = re.split(r'(?<=[.!?])\s+', html)
    return " ".join(s for s in sentences if not filler_re.match(s.strip()))


def _deduplicate_content(html: str) -> str:
    if not html:
        return html
    seen = set()
    result = []
    for part in re.split(r'(<[^>]+>)', html):
        if part.startswith('<'):
            result.append(part)
        else:
            unique = []
            for s in re.split(r'(?<=[.!?])\s+', part):
                norm = re.sub(r'\s+', ' ', s.strip().lower())
                if norm and norm not in seen:
                    seen.add(norm)
                    unique.append(s)
            result.append(' '.join(unique))
    return ''.join(result)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION-LEVEL PROMPTS
# Each prompt is tightly scoped to produce 300–400 words of UNIQUE content
# for exactly one section. No generic filler, no repeated statistics.
# ─────────────────────────────────────────────────────────────────────────────
SECTION_PROMPTS = {
    "introduction": """Write a high-impact Introduction and Executive Summary for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- Open with a specific, provocative claim or statistic about {topic}.
- 3–5 full paragraphs, each 80–120 words.
- Cite specific standards (e.g. NCC, Passive House) and real numbers.
- End with a transition to the next section.

OUTPUT FORMAT — raw HTML only, no markdown:
<p>[Opening paragraph — bold claim + context]</p>
<p>[Subsequent paragraphs — strategic depth + citations]</p>
<h3>[Subheading about the stakes]</h3>
<p>[What happens if they ignore this — specific outcome]</p>

Pain Points: {pain_points}
Firm USP: {firm_usp}""",

    "industry_challenges": """Write a detailed Common Challenges section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Describe 4 specific, non-obvious challenges — each with its own <h3>.
- Use specific numbers, percentages, dollar figures.
- Cite specific standards and real numbers.

OUTPUT FORMAT:
<h3>[Challenge 1 Name]</h3>
<p>[Deep analysis of the problem. 80-120 words.]</p>
<p><strong>Real cost:</strong> [Specific financial or timeline impact.]</p>
[Repeat for challenges 2, 3, 4]

Pain Points: {pain_points}""",

    "core_principles": """Write a Key Principles section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Define the 3 foundational pillars of success.
- Cite specific standards and real numbers.

OUTPUT FORMAT:
<p>[Opening: why these principles are non-negotiable. 80-120 words.]</p>
<h3>Principle 1: [Technical Name]</h3>
<p>[Detailed explanation. 80-120 words.]</p>
[Repeat for Principles 2 and 3]""",

    "practical_strategies": """Write a Practical Strategies section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- 3 actionable strategies.
- Cite specific standards and real numbers.

OUTPUT FORMAT:
<h3>Strategy 1: [Action-Oriented Name]</h3>
<p>[Detailed step-by-step execution. 80-120 words.]</p>
[Repeat for Strategies 2 and 3]""",

    "risk_management": """Write a Managing Risks section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Outline risk mitigation frameworks.
- Cite specific standards and real numbers.

OUTPUT FORMAT:
<h3>[Risk Name]</h3>
<p>[Analysis and mitigation. 80-120 words.]</p>
[Repeat for Risks 2 and 3]""",

    "best_practices": """Write a Best Practices section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Distill elite best practices.
- Cite specific standards and real numbers.

OUTPUT FORMAT:
<h3>[Best Practice Name]</h3>
<p>[Detailed strategy and impact. 80-120 words.]</p>
[Repeat for Practices 2, 3, 4]""",

    "key_statistics": """Write a Facts and Figures section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Present data-driven insights.
- Cite specific sources and real numbers.

OUTPUT FORMAT:
<h3>Analytical Data Points</h3>
<ul>
<li><strong>[Metric]:</strong> [Deep analysis. 80-120 words.]</li>
</ul>
[Repeat for 4 metrics]""",

    "implementation_roadmap": """Write an Implementation Roadmap section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Define the strategic timeline.
- Cite specific standards and real numbers.

OUTPUT FORMAT:
<h3>Phase 1: [Phase Name]</h3>
<p>[Detailed roadmap. 80-120 words.]</p>
[Repeat for Phases 2-5]""",

    "traditional_vs_modern": """Write a Traditional vs Modern section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Compare legacy vs modern approaches.
- Cite specific standards and real numbers.

OUTPUT FORMAT:
<h3>[Dimension Name]</h3>
<p><strong>Traditional:</strong> [Analysis. 60-80 words.]</p>
<p><strong>Modern:</strong> [Analysis. 60-80 words.]</p>
[Repeat for 4 dimensions]""",

    "case_study": """Write a Real World Example section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Provide a detailed client success story.
- Cite real numbers and outcomes.

OUTPUT FORMAT:
<h3>Case Study: [Project Name]</h3>
<p>[Context, Challenge, Solution, Result. 300+ words total.]</p>""",

    "expert_insights": """Write an Expert Insights section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Provide high-level expert analysis.
- Cite specific standards and real numbers.

OUTPUT FORMAT:
<h3>Expert Perspective: [Topic]</h3>
<p>[Nuanced analysis. 100-150 words.]</p>
[Repeat for 2-3 insights]""",

    "conclusion": """Write a Ready to Start closing section for a {lead_magnet_type} on **{topic}** for **{audience}**.

RULES:
- MINIMUM 300 words.
- 3–5 full paragraphs, each 80–120 words.
- Create a powerful call to action.
- Summarize why the firm is the logical choice.

OUTPUT FORMAT:
<h3>Partnering for Success</h3>
<p>[Persuasive closing. 300+ words total.]</p>""",
}

# Section maps
_SECTION_MAPS: Dict[str, Dict[str, str]] = {
    "guide": {
        "introduction": "introduction", "overview": "introduction", "executive_summary": "introduction",
        "common_challenges": "industry_challenges", "challenges": "industry_challenges", "industry_challenges": "industry_challenges",
        "key_principles": "core_principles", "principles": "core_principles", "core_principles": "core_principles",
        "practical_strategies": "practical_strategies", "strategies": "practical_strategies",
        "managing_risks": "risk_management", "risks": "risk_management", "risk_management": "risk_management",
        "best_practices": "best_practices",
        "facts_and_figures": "key_statistics", "facts": "key_statistics", "key_statistics": "key_statistics",
        "implementation_roadmap": "implementation_roadmap", "roadmap": "implementation_roadmap",
        "traditional_vs_modern": "traditional_vs_modern", "comparison": "traditional_vs_modern",
        "real_world_example": "case_study", "example": "case_study", "case_study": "case_study",
        "expert_insights": "expert_insights", "insights": "expert_insights",
        "ready_to_start": "conclusion", "conclusion": "conclusion",
    },
}

_UNIVERSAL_SLUG_MAP = {
    "introduction": "introduction", "overview": "introduction", "executive_summary": "introduction",
    "challenges": "industry_challenges", "industry_challenges": "industry_challenges",
    "principles": "core_principles", "core_principles": "core_principles",
    "strategies": "practical_strategies", "practical_strategies": "practical_strategies",
    "risks": "risk_management", "risk_management": "risk_management",
    "tips": "best_practices", "best_practices": "best_practices",
    "facts": "key_statistics", "key_statistics": "key_statistics", "data": "key_statistics",
    "roadmap": "implementation_roadmap", "implementation_roadmap": "implementation_roadmap",
    "comparison": "traditional_vs_modern", "traditional_vs_modern": "traditional_vs_modern",
    "case": "case_study", "case_study": "case_study", "example": "case_study",
    "insights": "expert_insights", "expert_insights": "expert_insights",
    "conclusion": "conclusion", "ready_to_start": "conclusion",
}


class GroqClient:
    SECTIONS = SECTIONS
    DOC_TYPE_LABELS = DOC_TYPE_LABELS
    _TYPE_MAP = _TYPE_MAP
    SECTION_LAYOUT = {key: layout for key, _, _, layout, _ in SECTIONS}

    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        self.client      = Groq(api_key=api_key) if api_key else None
        self.model       = "llama-3.3-70b-versatile"
        self.temperature = 0.65
        self.max_tokens  = 4096

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, Any]:
        raw_type = str(user_answers.get("document_type") or user_answers.get("lead_magnet_type") or "guide").strip()
        doc_type = _TYPE_MAP.get(raw_type) or _TYPE_MAP.get(raw_type.lower().replace("-","_").replace(" ","_"), "guide")

        pain_points = user_answers.get("pain_points", [])
        audience    = user_answers.get("target_audience", "Stakeholders")
        raw_topic   = user_answers.get("main_topic", "Strategic Design")
        topic       = _clean_topic_slug(str(raw_topic))

        return {
            "topic":           topic,
            "audience":        ", ".join(audience) if isinstance(audience, list) else str(audience),
            "pain_points":     ", ".join(pain_points) if isinstance(pain_points, list) else str(pain_points),
            "psychographics":  str(user_answers.get("psychographics", "")).strip(),
            "firm_usp":        str(user_answers.get("firm_usp", "")).strip(),
            "desired_outcome": user_answers.get("desired_outcome", ""),
            "tone":            user_answers.get("tone", "Professional and Friendly"),
            "industry":        user_answers.get("industry", "Architecture and Design"),
            "document_type":   doc_type,
        }

    def generate_lead_magnet_json(self, signals: Dict[str, Any], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        TWO-PASS GENERATION:
        Pass 1 — Generate title + all 12 section contents individually.
                  Each section gets its own focused API call with a tight prompt.
                  This guarantees every section has real content.
        Pass 2 — Assemble into the expected output structure.
        """
        doc_type   = signals.get("document_type", "guide")
        type_label = DOC_TYPE_LABELS.get(doc_type) or DOC_TYPE_LABELS["guide"]
        topic      = signals["topic"]
        audience   = signals["audience"]
        pain_points = signals.get("pain_points", "")
        firm_usp   = signals.get("firm_usp", "None")

        logger.info(f"🚀 Two-pass generation | type={doc_type} | topic={topic}")

        # ── Pass 1a: Generate title ──────────────────────────────────────────
        title_prompt = (
            f"Generate a professional, high-impact title and subtitle for a {type_label} on '{topic}' for {audience}.\n"
            f"Format exactly as: TITLE: [title here]\nSUBTITLE: [subtitle here]\n"
            f"Rules:\n"
            f"- The TITLE must prominently feature the core topic '{topic}'. Avoid being too metaphorical.\n"
            f"- Title should be 3-6 words, authoritative, and intellectual.\n"
            f"- Subtitle should be a complete sentence explaining the specific value proposition.\n"
            f"- Do NOT use the word 'sustainable-architecture' as a slug — use proper English words.\n"
            f"- No marketing fluff. Tone should be McKinsey-style."
        )
        title = topic
        subtitle = f"Strategic Insights for {topic}"
        try:
            title_resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You generate compelling document titles. Respond with exactly two lines: TITLE: ... and SUBTITLE: ..."},
                    {"role": "user", "content": title_prompt},
                ],
                temperature=0.7,
                max_tokens=100,
            )
            title_raw = title_resp.choices[0].message.content.strip()
            for line in title_raw.split("\n"):
                if line.upper().startswith("TITLE:"):
                    title = line.split(":", 1)[1].strip()
                elif line.upper().startswith("SUBTITLE:"):
                    subtitle = line.split(":", 1)[1].strip()
        except Exception as e:
            logger.warning(f"Title generation failed, using fallback: {e}")

        # ── Pass 1b: Generate each section individually ──────────────────────
        # Use the section_maps for this doc_type to determine which sections to generate
        type_map = _SECTION_MAPS.get(doc_type, _SECTION_MAPS["guide"])
        # Build reverse map: section_key → set of section names for this doc_type
        needed_keys = set(type_map.values())

        sections_content: Dict[str, str] = {}
        sections_titles: Dict[str, str] = {}

        system_msg = (
            "You are a senior architectural consultant writing premium lead magnet content. "
            "You write with authority and precision — dense with specific insight, real numbers, named standards. "
            "Never use placeholder text. Never truncate mid-sentence. Output raw HTML only."
        )

        for key, default_title, default_label, _, _ in SECTIONS:
            if key not in needed_keys:
                # Still generate it but it may not be used
                pass

            prompt_template = SECTION_PROMPTS.get(key)
            if not prompt_template:
                sections_content[key] = ""
                sections_titles[key] = default_title
                continue

            section_prompt = prompt_template.format(
                topic=topic,
                audience=audience,
                pain_points=pain_points,
                firm_usp=firm_usp,
                lead_magnet_type=type_label,
            )

            full_prompt = (
                f"Topic: {topic}\n"
                f"Audience: {audience}\n"
                f"Pain Points: {pain_points}\n\n"
                f"{section_prompt}\n\n"
                "CRITICAL: Output ONLY raw HTML. No markdown, no preamble, no sign-off. "
                "Every paragraph must be 70+ words. Do not use placeholder brackets like [STAT] or [EXAMPLE]. "
                "Do not repeat the same statistic twice. Minimum 300 words total."
            )

            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user",   "content": full_prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                content = resp.choices[0].message.content.strip()
                # Strip any markdown code fences if model added them
                content = re.sub(r'^```html?\s*', '', content, flags=re.IGNORECASE)
                content = re.sub(r'\s*```$', '', content)
                sections_content[key] = content
                sections_titles[key]  = default_title
                logger.info(f"  ✅ {key}: {len(content)} chars")
            except Exception as e:
                logger.error(f"  ❌ {key} generation failed: {e}")
                sections_content[key] = f"<p>Content for {default_title} could not be generated. Please try regenerating.</p>"
                sections_titles[key]  = default_title

        # ── Pass 2: Assemble output structure ────────────────────────────────
        sections_dict = {}
        for key in SECTION_KEYS:
            sections_dict[key] = {
                "content": sections_content.get(key, ""),
                "title":   sections_titles.get(key, ""),
            }

        logger.info(f"✅ Two-pass complete | {len([k for k,v in sections_content.items() if v])} sections filled")

        return {
            "title":               title,
            "subtitle":            subtitle,
            "document_type":       doc_type,
            "document_type_label": type_label,
            "sections":            sections_dict,
            "images":              [],
            "raw_output":          "",
        }

    def normalize_ai_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        sections_data = raw.get("sections", {})
        doc_type      = raw.get("document_type", "guide")

        normalized: Dict[str, Any] = {
            "title":               raw.get("title") or "",
            "subtitle":            raw.get("subtitle", ""),
            "document_type":       doc_type,
            "document_type_label": raw.get("document_type_label") or "",
            "sections_config":     self.SECTIONS,
            "framework":           {},
            "ai_images":           [],
        }

        for key, default_title, default_label, _, _ in SECTIONS:
            sec_data = sections_data.get(key, {})
            # Ensure we handle both dict and string content from Pass 1b
            if isinstance(sec_data, dict):
                content = sec_data.get("content", "")
                title   = sec_data.get("title", "") or default_title
            else:
                content = str(sec_data)
                title   = default_title

            sanitized = _strip_filler(_deduplicate_content(self._sanitize_html(str(content))))

            normalized[key] = sanitized
            normalized["framework"][key] = {"title": title or default_title, "kicker": default_label}

        normalized["summary"]              = normalized.get("introduction", "")[:500]
        normalized["cta_text"]             = normalized.get("conclusion", "")[:300]
        normalized["cta_headline"]         = normalized.get("cta_headline") or get_config("cta_headline", "Ready to Start Your Project?")
        normalized["legal_notice_summary"] = get_config("legal_notice_summary", "This document provides strategic guidance and should be verified by a qualified professional.")
        return normalized

    def map_to_template_vars(self, ai_content: Dict[str, Any], firm_profile: Dict[str, Any], signals: Dict[str, Any] = None) -> Dict[str, Any]:
        signals = signals or {}

        def fix_hex(c):
            if not c: return None
            s = str(c).strip()
            return s if s.startswith("#") else "#" + s

        primary_color   = fix_hex(firm_profile.get("primary_brand_color") or signals.get("primary_color")) or get_config("palette_primary", "#1a365d")
        secondary_color = fix_hex(firm_profile.get("secondary_brand_color")) or get_config("palette_secondary", "#c5a059")
        accent_color    = fix_hex(firm_profile.get("accent_color")) or get_config("palette_accent", "#f8fafc")

        # New palette variables for template
        white_color      = "#ffffff"
        light_color      = get_config("palette_light", "#f1f5f9")
        text_color       = get_config("palette_text", "#1e293b")
        text_light_color = get_config("palette_text_light", "#64748b")
        body_bg          = get_config("palette_body_bg", "#ffffff")
        border_radius    = get_config("layout_border_radius", "8px")

        work_email   = firm_profile.get("work_email", "")
        raw_name     = firm_profile.get("firm_name") or firm_profile.get("name") or ""
        company_name = _clean_company_name(raw_name, work_email) or signals.get("topic", "Strategic Analysis")

        topic    = _clean_topic_slug(str(signals.get("topic", "Industry Best Practices")))
        raw_sub  = ai_content.get("subtitle") or ""
        subtitle = _clean_topic_slug(raw_sub) if raw_sub and raw_sub.strip() != topic.strip() else f"Strategic Insights for {topic}"

        doc_type_label = ai_content.get("document_type_label") or "STRATEGIC GUIDE"

        cta_data: Dict[str, Any] = {}
        self._extract_cta(ai_content.get("conclusion", ""), cta_data)
        cta_headline = cta_data.get("ctaHeadline") or f"Ready to Implement Your {topic} Strategy?"
        cta_text = self._extract_support_text(ai_content.get("conclusion", "")) or (
            f"Take the next step in your {topic} journey. Book a complimentary consultation today."
        )

        vars: Dict[str, Any] = {
            "primaryColor":      primary_color,
            "secondaryColor":    secondary_color,
            "accentColor":       accent_color,
            "whiteColor":       white_color,
            "lightColor":       light_color,
            "textColor":        text_color,
            "textLightColor":   text_light_color,
            "bodyBackground":   body_bg,
            "borderRadius":      border_radius,
            "surfaceColor":      get_config("palette_surface", "#ffffff"),
            "onSurfaceColor":    get_config("palette_on_surface", "#1a202c"),
            "highlightColor":    get_config("palette_highlight", "#f4f7f9"),
            "documentTitle":     ai_content.get("title") or topic,
            "documentTypeLabel": doc_type_label,
            "mainTitle":         ai_content.get("title") or topic,
            "documentSubtitle":  subtitle,
            "companyName":       company_name,
            "emailAddress":      work_email,
            "phoneNumber":       firm_profile.get("phone_number", ""),
            "website":           firm_profile.get("firm_website", ""),
            "logoUrl":           firm_profile.get("firm_logo") or firm_profile.get("logo_url") or "",
            "logoPlaceholder":   company_name[:2].upper() if company_name else "AI",
            "footerText":        f"© {company_name} — Strategic Property Analysis",
            "differentiator":    firm_profile.get("branding_guidelines") or f"Expert {topic} solutions for {signals.get('audience', 'property owners')}.",
            "ctaHeadline":       cta_headline,
            "contactDescription": cta_text,
            "contentsTitle":     "Table of Contents",
            "termsTitle":        get_config("terms_title", "Terms of Use"),
            "summary":           ai_content.get("summary", ""),
            "image_1_url":       firm_profile.get("image_1_url") or signals.get("image_1_url"),
            "image_2_url":       firm_profile.get("image_2_url") or signals.get("image_2_url"),
        }

        # Terms
        vars.update({
            "termsSummary":    ai_content.get("legal_notice_summary") or f"This {doc_type_label} on {topic} is provided for informational purposes only.",
            "termsParagraph1": f"© {company_name}. All rights reserved.",
            "termsParagraph2": f"The information relates to {topic} and does not constitute legal, financial, or professional advice.",
            "termsParagraph3": "Readers are advised to verify all information independently before making business decisions.",
            "termsParagraph4": f"{company_name} accepts no liability for errors or outcomes arising from the use of this material.",
            "termsParagraph5": f"All strategic recommendations should be validated by a qualified {signals.get('industry','industry')} professional.",
        })

        # TOC HTML
        toc_html_parts = []
        for idx, (key, default_title, default_label, _, _) in enumerate(SECTIONS):
            fw_entry  = ai_content.get("framework", {}).get(key, {})
            sec_title = fw_entry.get("title") or default_title
            page_num  = str(idx + 4).zfill(2) # Page 1: Cover, 2: Terms, 3: TOC, 4: First Section
            target_id = f"section-{key}"
            toc_html_parts.append(
                f'<div class="toc-item">'
                f'<span class="toc-num">{str(idx+1).zfill(2)}</span>'
                f'<a href="#{target_id}" class="toc-label">{sec_title}</a>'
                f'<span class="toc-page">{page_num}</span>'
                f'</div>'
            )
        vars["toc_html"] = "\n".join(toc_html_parts)

        # Section vars — set once, protected
        for idx, (key, default_title, default_label, _, _) in enumerate(SECTIONS):
            fw_entry  = ai_content.get("framework", {}).get(key, {})
            sec_title = fw_entry.get("title") or default_title
            content   = ai_content.get(key, "")
            s_idx     = idx + 1

            # Map old executive_summary to introduction if needed
            if key == "introduction" and not content:
                content = ai_content.get("executive_summary", "")

            vars[f"customTitle{s_idx}"]   = sec_title
            vars[f"section_{key}_full_html"] = content # Full content injection for Template.html
            vars[f"section_{key}_id"] = f"section-{key}" # Fix missing anchor ID

            # Inject the standard title variable used in some templates
            vars[f"section_{key}_title"] = sec_title
            vars[f"section_{key}_kicker"] = fw_entry.get("kicker") or default_label
            
            # Plain text slots
            vars[f"section_{key}_intro"]   = self._extract_intro_text(content)
            vars[f"section_{key}_support"] = self._extract_support_text(content)

            # Stat
            stat_val, stat_lbl = self._extract_stat(content)
            vars[f"section_{key}_stat_val"] = stat_val
            vars[f"section_{key}_stat_lbl"] = stat_lbl

            # Bullets HTML — raw injection
            bullet_texts = self._extract_bullets_text(content)
            vars[f"section_{key}_bullets_html"] = "".join(f"<li>{bt}</li>" for bt in bullet_texts) if bullet_texts else ""

            # Image URL — only if real URL exists
            user_img_url = str(firm_profile.get(f"image_{s_idx}_url") or "").strip()
            vars[f"section_{key}_image_url"]     = user_img_url
            vars[f"section_{key}_image_caption"] = f"{sec_title} — Strategic Visual"

        # Page numbers
        for n in range(2, 16):
            vars[f"pageNumber{n}"]       = str(n).zfill(2)
            vars[f"pageNumberHeader{n}"] = str(n).zfill(2)

        return vars

    # ─────────────────────────────────────────────────────────────────────
    # EXTRACTION HELPERS — all return plain text
    # ─────────────────────────────────────────────────────────────────────

    def _html_to_text(self, html: str) -> str:
        if not html: return ""
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()

    def _extract_intro_text(self, html: str, max_chars: int = 220) -> str:
        if not html: return ""
        match = re.search(r'<p>(.*?)</p>', html, re.S)
        text = self._html_to_text(match.group(1)) if match else self._html_to_text(re.split(r'<h[1-6]>', html, flags=re.I)[0])
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        last_end = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
        return text[:last_end + 1] if last_end > max_chars // 2 else truncated.rstrip() + "…"

    def _extract_support_text(self, html: str, max_chars: int = 400) -> str:
        if not html: return ""
        paras = re.findall(r'<p>(.*?)</p>', html, re.S)
        if len(paras) <= 1: return ""
        combined = " ".join(self._html_to_text(p) for p in paras[1:3])
        if len(combined) <= max_chars:
            return combined
        truncated = combined[:max_chars]
        last_end = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
        return combined[:last_end + 1] if last_end > max_chars // 2 else truncated.rstrip() + "…"

    def _extract_bullets_text(self, html: str) -> List[str]:
        items = re.findall(r'<li>(.*?)</li>', html, re.S)
        if not items:
            items = re.findall(r'<h3>(.*?)</h3>', html)
        return [self._html_to_text(item) for item in items[:5]]

    def _extract_stat(self, html: str) -> Tuple[str, str]:
        if not html: return ("", "")
        match = re.search(r'(\d+(?:\.\d+)?%\+?|\$\d+(?:\.\d+)?[MBKmb]?|\d{2,}(?:,\d{3})*)', html)
        if not match: return ("", "")
        val = match.group(1)
        start = max(0, match.start() - 80)
        end   = min(len(html), match.end() + 80)
        ctx   = self._html_to_text(html[start:end])
        for kw in ["efficiency", "savings", "roi", "reduction", "increase", "growth", "improvement", "energy", "cost"]:
            if kw in ctx.lower():
                return (val, kw.title())
        return (val, "Key Metric")

    def _extract_cta(self, html: str, data: Dict):
        match = re.search(r'<h3>(.*?)</h3>', html)
        if match:
            data["ctaHeadline"] = self._html_to_text(match.group(1))

    def _sanitize_html(self, html: str) -> str:
        if not html: return html
        html = html.strip().strip('"')
        html = re.sub(r'<(/?)(\w+)([^>]*)>', lambda m: m.group(0) if m.group(2).lower() in ALLOWED_TAGS else "", html)
        return self._ensure_closed_tags(html).strip()

    def _ensure_closed_tags(self, html: str) -> str:
        void  = {"br", "hr", "img", "input", "link", "meta"}
        stack = []
        for closing, tag in re.findall(r"<(/?)([a-zA-Z1-6]+)", html):
            tag = tag.lower()
            if tag in void: continue
            if closing:
                if stack and stack[-1] == tag: stack.pop()
            else:
                stack.append(tag)
        for tag in reversed(stack):
            html += f"</{tag}>"
        return html

    def ensure_section_content(self, sections, signals, firm_profile):
        return sections
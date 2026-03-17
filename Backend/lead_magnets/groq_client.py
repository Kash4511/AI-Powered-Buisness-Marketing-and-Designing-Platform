import os
import re
import logging
import time
from typing import Dict, Any, List, Tuple
from groq import Groq

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION DEFINITIONS — 11 sections matching Template.html exactly
# ─────────────────────────────────────────────────────────────────────────────
SECTIONS = [
    ("executive_summary",      "Executive Summary",         "OVERVIEW",   "text-only", ""),
    ("industry_analysis",      "Industry Problem Analysis", "CHALLENGES", "text-only", ""),
    ("core_principles",        "Key Principles",            "PRINCIPLES", "text-only", ""),
    ("practical_strategies",   "Practical Implementation",  "STRATEGIES", "text-only", ""),
    ("business_benefits",      "Business Benefits",         "VALUE",      "text-only", ""),
    ("case_study",             "Real World Case Study",     "CASE STUDY", "text-only", ""),
    ("risk_management",        "Risk Management",           "RISK",       "text-only", ""),
    ("implementation_roadmap", "Implementation Roadmap",    "ROADMAP",    "text-only", ""),
    ("future_trends",          "Future Trends",             "TRENDS",     "text-only", ""),
    ("key_takeaways",          "Key Takeaways",             "SUMMARY",    "text-only", ""),
    ("call_to_action",         "Call to Action",            "NEXT STEPS", "text-only", ""),
]

SECTION_KEYS = [s[0] for s in SECTIONS]

DOC_TYPE_LABELS = {
    "guide": "Strategic Guide", "case_study": "Case Study Report",
    "checklist": "Implementation Checklist", "roi_calculator": "ROI Analysis Report",
    "trends_report": "Industry Trends Report", "design_portfolio": "Design Portfolio",
    "client_onboarding": "Client Onboarding Guide", "custom": "Strategic Report",
}

_TYPE_MAP = {
    "guide": "guide", "strategic_guide": "guide", "Guide": "guide", "Strategic Guide": "guide",
    "case_study": "case_study", "Case Study": "case_study",
    "checklist": "checklist", "Checklist": "checklist",
    "roi_calculator": "roi_calculator", "ROI Calculator": "roi_calculator",
    "trends_report": "trends_report", "Trends Report": "trends_report",
    "design_portfolio": "design_portfolio", "Design Portfolio": "design_portfolio",
    "client_onboarding": "client_onboarding", "client_onboarding_flow": "client_onboarding",
    "Client Onboarding": "client_onboarding", "Client Onboarding Flow": "client_onboarding",
    "custom": "custom", "Custom": "custom",
}

ALLOWED_TAGS = {"p", "strong", "em", "h3", "h4", "ul", "ol", "li", "br", "blockquote"}


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _clean_topic_slug(topic: str) -> str:
    if not topic:
        return topic
    return " ".join(w.capitalize() for w in topic.replace("-", " ").replace("_", " ").split())


def _clean_company_name(name: str, email: str = "") -> str:
    if not name:
        if email and "@" in email:
            domain = email.split("@")[-1].split(".")[0]
            if domain.lower() not in ("gmail","yahoo","hotmail","outlook","icloud","me","mac"):
                return domain.replace("-"," ").replace("_"," ").title()
        return name
    is_username = " " not in name.strip() and "@" not in name and (
        re.search(r'\d', name) or name == name.lower()
    )
    if not is_username:
        return name
    if email and "@" in email:
        domain = email.split("@")[-1].split(".")[0]
        if domain.lower() not in ("gmail","yahoo","hotmail","outlook","icloud","me","mac"):
            return domain.replace("-"," ").replace("_"," ").title()
    return re.sub(r'\d+$', '', name).title() or name


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


def _sanitize_html(html: str) -> str:
    if not html:
        return html
    html = html.strip().strip('"')
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'^#{1,6}\s+.*$', '', html, flags=re.MULTILINE)
    html = re.sub(r'\[[A-Z][^\]]{2,80}\]', '', html)
    html = re.sub(
        r'<(/?)(\w+)([^>]*)>',
        lambda m: m.group(0) if m.group(2).lower() in ALLOWED_TAGS else "",
        html
    )
    return _ensure_closed_tags(html).strip()


def _ensure_closed_tags(html: str) -> str:
    void = {"br","hr","img","input","link","meta"}
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


# ─────────────────────────────────────────────────────────────────────────────
# SECTION PROMPTS — one per section, each enforcing min 300 words,
# banning repeated stats, banning first-person firm voice, requiring
# named standards and specific figures.
# ─────────────────────────────────────────────────────────────────────────────
SECTION_PROMPTS = {

"executive_summary": """\
Write a 350-400 word Executive Summary for a {lead_magnet_type} on **{topic}** for **{audience}**.

STRICT RULES:
- The content must be 100% specific to **{topic}** — not generic business advice.
- Start with a striking fact, statistic, or market reality about **{topic}** right now. NOT "In this guide" or "Welcome".
- Paragraph 1 (120+ words): Why **{topic}** is urgent for **{audience}** right now. Reference a real market condition, regulation, or pain point specific to this topic.
- Paragraph 2 (120+ words): The commercial or strategic opportunity that mastering **{topic}** creates — cost savings, revenue, efficiency, competitive edge, compliance — specific to this topic.
- Paragraph 3 (100+ words): What this guide delivers to **{audience}**. Name specific outcomes they will gain.
- Reference at least one named framework, standard, tool, methodology, or regulation relevant to **{topic}**.
- Zero filler phrases ("In conclusion...", "It is important to note..."). Zero "our firm" or "we believe".
- Every sentence must reference **{topic}** or the pain points: {pain_points}
Output: raw HTML only. <p> for paragraphs. <strong> for key terms/numbers. No markdown.""",

"industry_analysis": """\
Write a 380-420 word Industry Problem Analysis on **{topic}** for **{audience}**.

The problems MUST be specific to **{topic}** — not generic business problems.
Pain points to address: {pain_points}

STRUCTURE — exactly 4 problems, each with its own <h3>:
  <h3>[Problem Name — specific to {topic}]</h3>
  <p>[What triggers this problem in the context of {topic}. 80-100 words. Name a real constraint, cost driver, or failure mode specific to this topic.]</p>
  <p><strong>Real impact on {audience}:</strong> [Specific financial, operational, or strategic consequence. 50-70 words.]</p>

PROBLEM CATEGORIES (one each, adapted to {topic}):
1. Financial / cost problem specific to {topic}
2. Compliance, regulatory, or standards problem specific to {topic}
3. Technical or operational execution problem specific to {topic}
4. People, communication, or stakeholder problem specific to {topic}

RULES: Every problem is anchored to {topic}. Each includes a specific figure, cost, or measurable consequence. No two share a statistic.
Output: raw HTML only.""",

"core_principles": """\
Write a 380-420 word Key Principles section on **{topic}** for **{audience}**.

All principles MUST be specific to **{topic}** — derived from how this topic actually works.

STRUCTURE:
  <p>[60-80 word intro: why these principles are foundational for anyone working in {topic}]</p>
  <h3>Principle 1: [Name specific to {topic}]</h3>
  <p>[What this principle means in the context of {topic}, why it matters, real-world consequence of ignoring it. 80-100 words.]</p>
  <h3>Principle 2: [Different aspect of {topic}]</h3>
  <p>[80-100 words. Different domain from Principle 1.]</p>
  <h3>Principle 3: [Different aspect of {topic}]</h3>
  <p>[80-100 words. Different domain.]</p>
  <h3>Principle 4: [Different aspect of {topic}]</h3>
  <p>[80-100 words. Different domain.]</p>

RULES: Each principle covers a genuinely different aspect of {topic}. Reference named tools, frameworks, or standards where relevant to this specific topic. No repeated statistics.
Output: raw HTML only.""",

"practical_strategies": """\
Write a 380-420 word Practical Strategies section on **{topic}** for **{audience}**.

All strategies MUST be specific and actionable for **{topic}** — not generic advice.
Address these pain points: {pain_points}

STRUCTURE — 3 strategies, each covering a different phase or dimension of {topic}:
  <h3>Strategy [N]: [Action-Verb Name specific to {topic}]</h3>
  <p>[How to execute this strategy in the context of {topic}. Name specific tools, methods, or frameworks relevant to this topic. 100-120 words.]</p>
  <ul>
    <li><strong>Expected outcome:</strong> [Specific measurable benefit — a real number or result achievable in {topic}]</li>
    <li><strong>Common mistake to avoid:</strong> [The specific error people make in {topic} that kills this strategy]</li>
    <li><strong>Key resource:</strong> [Named tool, platform, methodology, or framework used in {topic}]</li>
  </ul>

RULES: Each strategy is for a different phase or dimension of {topic}. No strategy can share a statistic with another. No generic openers.
Output: raw HTML only.""",

"business_benefits": """\
Write a 380-420 word Business Benefits section on **{topic}** for **{audience}**.

Benefits MUST be specific to what **{topic}** actually delivers — not generic business benefits.

STRUCTURE — 3 benefit areas:
  <h3>[Benefit Area — specific outcome from {topic}]</h3>
  <p>[Strategic analysis explaining exactly how {topic} delivers this benefit. Include a credible figure or data point specific to this domain. 120-140 words.]</p>

BENEFIT ORDER (adapt names to {topic}):
1. Financial return, cost saving, or revenue benefit specific to {topic}
2. Operational efficiency, time saving, or performance benefit specific to {topic}
3. Competitive, compliance, or reputation benefit specific to {topic}

RULES: Each benefit uses a DIFFERENT metric or figure. Benefits must feel specific to {topic}, not copy-pasted from a generic guide. Write for a reader who will verify claims.
Output: raw HTML only.""",

"case_study": """\
Write a 420-480 word Real World Case Study on **{topic}** for **{audience}**.

The case study MUST be about {topic} — not a generic business story.

STRUCTURE:
  <h3>Case Study: [Descriptive Name specific to {topic}]</h3>
  <p><strong>Context:</strong> [Organisation type, scale, location type, profile of the people involved. Specific to {topic}. 60-80 words.]</p>
  <p><strong>The challenge:</strong> [The specific problem they faced with {topic}. Name the exact constraint or failure. 80-100 words.]</p>
  <p><strong>The approach:</strong> [The specific strategies, tools, and methods they used — all relevant to {topic}. No generics. 100-120 words.]</p>
  <p><strong>Measured outcomes:</strong> [At least 3 specific quantified results from applying {topic} principles — use different metrics for each. 80-100 words.]</p>
  <p><strong>Transferable lesson:</strong> [The single most applicable insight for {audience} working on {topic}. 50-70 words.]</p>

RULES: Every element of this case study is anchored to {topic}. Real numbers. No two outcomes the same percentage. No "our firm" language.
Output: raw HTML only.""",

"risk_management": """\
Write a 380-420 word Risk Management section on **{topic}** for **{audience}**.

Risks MUST be specific to **{topic}** — the real failure modes and dangers in this domain.

STRUCTURE — 3 non-obvious risks specific to {topic}:
  <h3>[Risk Name — a real, specific risk in {topic}]</h3>
  <p>[How this risk manifests in {topic}, what triggers it, why it catches people off guard. 80-100 words.]</p>
  <p><strong>Professional mitigation:</strong> [Specific action, process, tool, or safeguard that prevents this risk in {topic}. 70-90 words.]</p>

RISK CATEGORIES (adapted to {topic}):
1. Execution or technical risk specific to {topic}
2. Compliance, legal, or standards risk specific to {topic}
3. Strategic or commercial risk specific to {topic}

RULES: Each risk is genuinely specific to {topic} — not a risk that could apply to any industry. Each mitigation references a specific action, document type, or process relevant to {topic}.
Output: raw HTML only.""",

"implementation_roadmap": """\
Write a 380-420 word Implementation Roadmap for **{topic}** for **{audience}**.

The phases MUST reflect how {topic} is actually implemented — not a generic project plan.

STRUCTURE — exactly 6 phases adapted to how {topic} works:
  <h3>Phase [N]: [Phase Name relevant to {topic}] — [Typical Duration]</h3>
  <p>[What happens in this phase specific to {topic}, who is responsible, what the deliverable is. 70-90 words.]</p>

Generate 6 sequential phases that reflect the ACTUAL workflow for implementing {topic}.
Phase names and durations should be realistic for this specific topic.
Each phase must have a clear start trigger and end deliverable specific to {topic}.

RULES: Phases must match how {topic} is actually done — not generic project management. No overlap.
Output: raw HTML only.""",

"future_trends": """\
Write a 380-420 word Future Trends section on **{topic}** for **{audience}**.

Trends MUST be specific to **{topic}** — what is actually changing in this domain.

STRUCTURE — 4 trends that are genuinely emerging in {topic}:
  <h3>[Trend Name — specific to {topic}]</h3>
  <p>[What is driving this trend in {topic}, when it is expected to mainstream, what {audience} must do NOW to prepare. 100-120 words. Reference specific technologies, regulations, tools, or market forces relevant to {topic}.]</p>

Generate 4 real, emerging trends in the domain of {topic} — not generic technology trends.
Each trend must explain WHY it is happening in {topic} specifically.
Each must include a timeline or market figure.
No two trends can share the same driver or statistic.

RULES: All trends are anchored to {topic}. Generic tech trends (AI, automation) only included if directly relevant to {topic}.
Output: raw HTML only.""",

"key_takeaways": """\
Write a 300-350 word Key Takeaways section for **{topic}** for **{audience}**.

Takeaways MUST synthesise what was covered about **{topic}** — not generic insights.

STRUCTURE:
  <h3>What Every {audience} Must Know About {topic}</h3>
  <p>[60-80 word framing: why these 5 insights from this guide on {topic} are the most actionable]</p>
  <ul>
    <li><strong>[Label from {topic}]:</strong> [Insight specific to {topic} that synthesises the challenges section. 40-60 words.]</li>
    <li><strong>[Label from {topic}]:</strong> [Insight specific to {topic} from the strategies section. Actionable. 40-60 words.]</li>
    <li><strong>[Label from {topic}]:</strong> [Insight specific to {topic} from the risks section. Protective. 40-60 words.]</li>
    <li><strong>[Label from {topic}]:</strong> [Insight specific to {topic} from the benefits section. Commercial. 40-60 words.]</li>
    <li><strong>[Label from {topic}]:</strong> [Insight specific to {topic} from the trends section. Forward-looking. 40-60 words.]</li>
  </ul>
  <p>[50-70 word closing: the single most important next action for {audience} regarding {topic}]</p>

RULES: Every takeaway references {topic} explicitly. No repeated statistics.
Output: raw HTML only.""",

"call_to_action": """\
Write a 350-400 word Call to Action close for a guide on **{topic}** for **{audience}**.

The CTA must be relevant to **{topic}** — reference the specific value and context of this guide.

STRUCTURE:
  <h3>[Compelling heading that references {topic} and the reader's situation]</h3>
  <p>[100-120 words: Acknowledge what the reader now understands about {topic}. Reference a specific challenge or opportunity from {topic} that makes acting now smarter than waiting. No generic language.]</p>
  <h3>What Working Together Looks Like</h3>
  <p>[100-120 words: Describe the first engagement concretely — what questions get answered about {topic}, what the reader walks away with, why it is low-risk. Make it specific to {topic}.]</p>
  <h3>Why {topic} Expertise Matters Now</h3>
  <p>[80-100 words: One specific reason tied to current market conditions, emerging requirements, or competitive pressure in {topic} that makes acting in the next 90 days smarter than deferring.]</p>

RULES: Every paragraph references {topic}. Zero "contact us today" without context. Zero "At our firm, we believe". Write as a trusted adviser.
Output: raw HTML only.""",
}


# ─────────────────────────────────────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class GroqClient:
    SECTIONS        = SECTIONS
    SECTION_KEYS    = SECTION_KEYS
    DOC_TYPE_LABELS = DOC_TYPE_LABELS
    _TYPE_MAP       = _TYPE_MAP
    SECTION_LAYOUT  = {key: layout for key, _, _, layout, _ in SECTIONS}

    def __init__(self, api_key: str = None):
        api_key      = api_key or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        self.client      = Groq(api_key=api_key) if api_key else None
        self.model       = "llama-3.3-70b-versatile"
        self.temperature = 0.60
        self.max_tokens  = 4096

    # ──────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, Any]:
        raw_type = str(
            user_answers.get("document_type") or
            user_answers.get("lead_magnet_type") or "guide"
        ).strip()
        doc_type = (
            _TYPE_MAP.get(raw_type) or
            _TYPE_MAP.get(raw_type.lower().replace("-","_").replace(" ","_"), "guide")
        )
        pain_points = user_answers.get("pain_points", [])
        audience    = user_answers.get("target_audience", "Stakeholders")
        return {
            "topic":           _clean_topic_slug(str(user_answers.get("main_topic", "Strategic Design"))),
            "audience":        ", ".join(audience) if isinstance(audience, list) else str(audience),
            "pain_points":     ", ".join(pain_points) if isinstance(pain_points, list) else str(pain_points),
            "psychographics":  str(user_answers.get("psychographics", "")).strip(),
            "firm_usp":        str(user_answers.get("firm_usp", "")).strip(),
            "desired_outcome": user_answers.get("desired_outcome", ""),
            "tone":            user_answers.get("tone", "Professional"),
            "industry":        user_answers.get("industry", ""),
            "document_type":   doc_type,
        }

    def generate_lead_magnet_json(
        self, signals: Dict[str, Any], firm_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        TWO-PASS GENERATION:
        Pass 1a — One small call to generate the document title (100 tokens)
        Pass 1b — One focused API call per section (11 calls × up to 4096 tokens each)
                  This GUARANTEES every page has full, deep content.
                  A single 4096-token call can never fill 11 sections — this is the fix.
        Pass 2  — Assemble into the return structure
        """
        doc_type    = signals.get("document_type", "guide")
        type_label  = DOC_TYPE_LABELS.get(doc_type) or DOC_TYPE_LABELS["guide"]
        topic       = signals["topic"]
        audience    = signals["audience"]
        pain_points = signals.get("pain_points", "")
        firm_usp    = signals.get("firm_usp", "")

        logger.info(f"🚀 Two-pass | type={doc_type} | topic={topic[:40]}")

        # ── Pass 1a: Title ─────────────────────────────────────────────────
        title    = ""
        subtitle = ""
        try:
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You write authoritative document titles. "
                            "Respond with EXACTLY two lines:\n"
                            "TITLE: [3-6 word title prominently featuring the core topic]\n"
                            "SUBTITLE: [One sentence value proposition for the target audience]"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Topic: '{topic}' | Audience: {audience} | Type: {type_label}\n"
                            f"Rules: McKinsey-style, no hyphens/slugs, no marketing fluff, "
                            f"title must feature '{topic}' clearly."
                        ),
                    },
                ],
                temperature=0.7,
                max_tokens=120,
            )
            for line in r.choices[0].message.content.strip().split("\n"):
                if line.upper().startswith("TITLE:"):
                    title = line.split(":", 1)[1].strip()
                elif line.upper().startswith("SUBTITLE:"):
                    subtitle = line.split(":", 1)[1].strip()
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")

        # ── Pass 1b: Per-section generation ───────────────────────────────
        system_msg = (
            f"You are a senior expert consultant and premium professional report writer "
            f"specialising in {topic}. "
            "Every response is raw HTML only — zero markdown, zero preamble, zero sign-off, zero code fences. "
            f"Content must be 100% specific to {topic} — dense with insight, real examples, "
            f"named tools/frameworks/standards relevant to {topic}, and credible figures. "
            "Minimum 300 words per response. Never repeat statistics across paragraphs. "
            "Never use first-person firm voice ('our firm', 'we believe', 'our team'). "
            "Write as an independent expert adviser to someone who works in or with this topic every day."
        )

        sections_content: Dict[str, str] = {}

        for key, default_title, default_label, _, _ in SECTIONS:
            prompt_template = SECTION_PROMPTS.get(key, "")
            if not prompt_template:
                sections_content[key] = f"<p><strong>{default_title}</strong></p>"
                continue

            try:
                section_prompt = prompt_template.format(
                    topic=topic, audience=audience,
                    pain_points=pain_points, firm_usp=firm_usp,
                    lead_magnet_type=type_label,
                )
            except KeyError:
                section_prompt = prompt_template

            user_msg = (
                f"TOPIC: {topic}\n"
                f"AUDIENCE: {audience}\n"
                f"PAIN POINTS: {pain_points}\n\n"
                f"WRITE SECTION: {default_title}\n\n"
                f"{section_prompt}\n\n"
                "CRITICAL: MINIMUM 300 words. Raw HTML only. "
                "No placeholders like [STAT] or [INSERT EXAMPLE]. No truncation."
            )

            try:
                resp    = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user",   "content": user_msg},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                raw = resp.choices[0].message.content.strip()
                # Strip accidental code fences
                raw = re.sub(r'^```html?\s*', '', raw, flags=re.IGNORECASE)
                raw = re.sub(r'\s*```\s*$', '', raw)
                # Sanitize
                raw = _sanitize_html(raw)
                sections_content[key] = raw
                logger.info(f"  ✅ {key}: {len(raw)} chars")
            except Exception as e:
                logger.error(f"  ❌ {key}: {e}")
                sections_content[key] = (
                    f"<p>Content for <strong>{default_title}</strong> could not be generated. "
                    f"Please regenerate this document.</p>"
                )

        # ── Pass 2: Assemble ───────────────────────────────────────────────
        filled = sum(1 for k in SECTION_KEYS if len(sections_content.get(k,"")) > 100)
        logger.info(f"✅ Complete | {filled}/{len(SECTION_KEYS)} sections filled")

        return {
            "title":               title,
            "subtitle":            subtitle,
            "document_type":       doc_type,
            "document_type_label": type_label,
            "sections": {
                key: {"content": sections_content.get(key,""), "title": dtitle}
                for key, dtitle, *_ in SECTIONS
            },
        }

    def normalize_ai_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        sections_data = raw.get("sections", {})
        doc_type      = raw.get("document_type", "guide")

        normalized: Dict[str, Any] = {
            "title":               raw.get("title") or "",
            "subtitle":            raw.get("subtitle", ""),
            "document_type":       doc_type,
            "document_type_label": raw.get("document_type_label") or "",
            "framework":           {},
        }

        for key, default_title, default_label, _, _ in SECTIONS:
            sec_data = sections_data.get(key, {})
            content  = sec_data.get("content","") if isinstance(sec_data, dict) else str(sec_data)
            title    = (sec_data.get("title","") if isinstance(sec_data, dict) else "") or default_title

            normalized[key] = _sanitize_html(str(content))
            normalized["framework"][key] = {"title": title or default_title, "kicker": default_label}

        normalized["summary"]              = normalized.get("executive_summary","")[:500]
        normalized["legal_notice_summary"] = (
            "This document provides strategic guidance only and should be verified "
            "by a qualified professional before implementation."
        )
        return normalized

    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Dict[str, Any],
        signals: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        signals = signals or {}

        def _fix_hex(c):
            if not c: return None
            s = str(c).strip().lstrip("#")
            return f"#{s}" if len(s) == 6 else None

        primary_color   = _fix_hex(firm_profile.get("primary_brand_color") or signals.get("primary_color")) or "#1a365d"
        secondary_color = _fix_hex(firm_profile.get("secondary_brand_color")) or "#c5a059"
        accent_color    = _fix_hex(firm_profile.get("accent_color")) or "#f8fafc"

        work_email   = firm_profile.get("work_email", "")
        raw_name     = firm_profile.get("firm_name") or firm_profile.get("name") or ""
        company_name = _clean_company_name(raw_name, work_email)

        topic    = _clean_topic_slug(str(signals.get("topic", "")))
        raw_sub  = ai_content.get("subtitle") or ""
        # Use AI subtitle if it exists and isn't just the topic repeated; otherwise empty
        subtitle = (
            _clean_topic_slug(raw_sub)
            if raw_sub and raw_sub.strip().lower() != topic.strip().lower()
            else ""
        )
        doc_type_label = ai_content.get("document_type_label") or ""

        # CTA headline — from AI-generated call_to_action section only
        cta_html  = ai_content.get("call_to_action","")
        h3_match  = re.search(r'<h3>(.*?)</h3>', cta_html)
        cta_headline = _html_to_text(h3_match.group(1)) if h3_match else ""

        vars: Dict[str, Any] = {
            # CSS vars
            "primaryColor":   primary_color,
            "secondaryColor": secondary_color,
            "accentColor":    accent_color,
            "highlightColor": "#f4f7f9",
            "lightColor":     "#f1f5f9",
            "whiteColor":     "#ffffff",
            "textColor":      "#1e293b",
            "textLightColor": "#64748b",
            "bodyBackground": "#ffffff",
            "borderRadius":   "8px",
            "surfaceColor":   "#ffffff",
            "onSurfaceColor": "#1a202c",
            # Document
            "documentTitle":     ai_content.get("title") or topic,
            "documentTypeLabel": doc_type_label,
            "mainTitle":         ai_content.get("title") or topic,
            "documentSubtitle":  subtitle,
            # Company
            "companyName":  company_name,
            "emailAddress": work_email,
            "phoneNumber":  firm_profile.get("phone_number",""),
            "website":      firm_profile.get("firm_website",""),
            "logoUrl":      firm_profile.get("firm_logo") or firm_profile.get("logo_url") or "",
            # Labels
            "contentsTitle": "Table of Contents",
            "ctaHeadline":   cta_headline,
            "termsTitle":    "Terms of Use & Disclaimer",
            # Terms
            "termsSummary":    ai_content.get("legal_notice_summary",""),
            "termsParagraph1": f"© {company_name}. All rights reserved.",
            "termsParagraph2": f"The information in this {doc_type_label} relates to {topic} and does not constitute legal, financial, or professional advice.",
            "termsParagraph3": "Readers are advised to verify all information independently before making project or business decisions.",
            "termsParagraph4": f"{company_name} accepts no liability for errors, omissions, or outcomes arising from the use of this material.",
            "termsParagraph5": f"All recommendations should be validated by a qualified {signals.get('industry', topic)} professional before implementation.",
        }

        # ── Image slots — ONLY set when a real URL exists ──────────────────
        # Absent key → {{#if image_N_url}} evaluates falsy → no broken placeholder
        for i in range(1, 7):
            url = str(firm_profile.get(f"image_{i}_url") or "").strip()
            if url:
                vars[f"image_{i}_url"] = url

        # ── TOC — pre-built HTML, no Handlebars loop needed ────────────────
        toc_parts = []
        for idx, (key, default_title, _, _, _) in enumerate(SECTIONS):
            fw    = ai_content.get("framework",{}).get(key,{})
            title = fw.get("title") or default_title
            page  = str(idx + 4).zfill(2)   # Cover=01, Terms=02, TOC=03, sections=04+
            toc_parts.append(
                f'<div class="toc-item">'
                f'<span class="toc-num">{str(idx+1).zfill(2)}</span>'
                f'<span class="toc-label">{title}</span>'
                f'<span class="toc-page">{page}</span>'
                f'</div>'
            )
        vars["toc_sections_html"] = "\n".join(toc_parts)
        vars["toc_html"]          = vars["toc_sections_html"]

        # ── Per-section vars ───────────────────────────────────────────────
        for idx, (key, default_title, default_label, _, _) in enumerate(SECTIONS):
            fw      = ai_content.get("framework",{}).get(key,{})
            title   = fw.get("title") or default_title
            content = ai_content.get(key,"")
            s_idx   = idx + 1

            # The template uses {{section_KEY_full_html}} — injected as raw HTML
            vars[f"customTitle{s_idx}"]          = title
            vars[f"section_{key}_full_html"]     = content   # ← raw HTML injection
            vars[f"section_{key}_id"]            = f"section-{key}"
            vars[f"section_{key}_title"]         = title
            vars[f"section_{key}_kicker"]        = default_label
            # Plain-text slots (for any legacy template parts)
            vars[f"section_{key}_intro"]         = self._extract_intro_text(content)
            vars[f"section_{key}_support"]       = self._extract_support_text(content)
            # Stat
            sv, sl = self._extract_stat(content)
            vars[f"section_{key}_stat_val"]      = sv
            vars[f"section_{key}_stat_lbl"]      = sl
            # Bullet HTML
            vars[f"section_{key}_bullets_html"]  = self._extract_bullets_html(content)

        # Page numbers
        for n in range(2, 16):
            vars[f"pageNumber{n}"]       = str(n).zfill(2)
            vars[f"pageNumberHeader{n}"] = str(n).zfill(2)

        return vars

    # ──────────────────────────────────────────────────────────────────────
    # EXTRACTION HELPERS
    # ──────────────────────────────────────────────────────────────────────

    def _extract_intro_text(self, html: str, max_chars: int = 220) -> str:
        if not html: return ""
        m    = re.search(r'<p>(.*?)</p>', html, re.S)
        text = _html_to_text(m.group(1)) if m else _html_to_text(html.split('<h')[0])
        if len(text) <= max_chars: return text
        trunc = text[:max_chars]
        end   = max(trunc.rfind('.'), trunc.rfind('!'), trunc.rfind('?'))
        return text[:end+1] if end > max_chars//2 else trunc.rstrip() + "…"

    def _extract_support_text(self, html: str, max_chars: int = 400) -> str:
        if not html: return ""
        paras = re.findall(r'<p>(.*?)</p>', html, re.S)
        if len(paras) <= 1: return ""
        combined = " ".join(_html_to_text(p) for p in paras[1:3])
        if len(combined) <= max_chars: return combined
        trunc = combined[:max_chars]
        end   = max(trunc.rfind('.'), trunc.rfind('!'), trunc.rfind('?'))
        return combined[:end+1] if end > max_chars//2 else trunc.rstrip() + "…"

    def _extract_bullets_html(self, html: str) -> str:
        items = re.findall(r'<li>(.*?)</li>', html, re.S)
        if not items:
            items = [re.sub(r'<[^>]+>',' ',h).strip() for h in re.findall(r'<h3>(.*?)</h3>', html)]
        return "".join(f"<li>{_html_to_text(it)}</li>" for it in items[:5])

    def _extract_stat(self, html: str) -> Tuple[str,str]:
        if not html: return ("","")
        m = re.search(r'(\d+(?:\.\d+)?%\+?|\$\d+(?:\.\d+)?[MBKmb]?|\d{2,}(?:,\d{3})*)', html)
        if not m: return ("","")
        val = m.group(1)
        ctx = _html_to_text(html[max(0,m.start()-80):min(len(html),m.end()+80)]).lower()
        for kw in ["efficiency","savings","roi","reduction","increase","growth","energy","cost"]:
            if kw in ctx: return (val, kw.title())
        return (val, "Key Metric")

    def ensure_section_content(self, sections, signals, firm_profile):
        return sections
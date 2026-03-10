import os
import json
import logging
import time
import re
import traceback as _tb
from typing import Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION DEFINITIONS — 11 deep content sections, each with a strict brief
# that forces specificity, real metrics, named tools, and zero filler.
# ─────────────────────────────────────────────────────────────────────────────
SECTIONS = [
    (
        "executive_summary",
        "Strategic Executive Overview",
        "OVERVIEW",
        "text-only",
        (
            "Write a razor-sharp Strategic Executive Overview for a professional guide on {topic} aimed at {audience}.\n"
            "RULES — break every one of these and the section FAILS:\n"
            "  • Never open with 'This section', 'This guide', 'In today's', or any meta-sentence.\n"
            "  • Every paragraph must contain at least one hard number or named standard (e.g. ISO 19650, 18% cost delta, 2.4x ROI).\n"
            "  • Name the single biggest shift happening RIGHT NOW in {topic} and why {audience} cannot afford to ignore it.\n"
            "STRUCTURE:\n"
            "<p>Opening provocation — a bold claim about the current state of {topic} backed by a specific industry stat.</p>\n"
            "<h3>Why This Moment Is Different</h3>\n"
            "<p>3–4 sentences on the macro forces (regulatory, technological, economic) converging right now. Name them explicitly.</p>\n"
            "<h3>The Cost of Inaction</h3>\n"
            "<p>Quantify what {audience} loses by staying with legacy approaches. Use a specific failure scenario tied to {pain_points}.</p>\n"
            "<h3>What This Guide Delivers</h3>\n"
            "<ul><li>Outcome 1 — specific and measurable</li><li>Outcome 2 — specific and measurable</li>"
            "<li>Outcome 3 — specific and measurable</li><li>Outcome 4 — specific and measurable</li></ul>\n"
            "TARGET: 380–420 words. Zero filler. Zero repetition."
        )
    ),
    (
        "key_challenges",
        "Critical Industry Challenges",
        "CHALLENGES",
        "image-right",
        (
            "Identify 4 specific, named technical and operational challenges facing {audience} in {topic}.\n"
            "RULES:\n"
            "  • Each challenge must have a NAME that reads like a diagnostic term (e.g. 'BIM-to-Field Data Decay', 'Tolerance Stack Failure').\n"
            "  • Do NOT use vague language like 'lack of communication' or 'inefficiency'.\n"
            "  • Each must tie directly to one pain point in: {pain_points}.\n"
            "STRUCTURE — repeat 4 times:\n"
            "<h3>[Diagnostic Challenge Name]</h3>\n"
            "<p><strong>Root Cause:</strong> The specific technical or process failure that creates this problem in {topic} workflows.</p>\n"
            "<p><strong>Real-World Impact:</strong> A concrete scenario — cost overrun, schedule slip, rework percentage, or client dispute — with a number.</p>\n"
            "<p><strong>Resolution Vector:</strong> The specific method, tool, or protocol that eliminates this challenge. Name the tool or standard.</p>\n"
            "TARGET: 380–420 words. Four distinct, named challenges. No filler sentences."
        )
    ),
    (
        "strategic_framework",
        "Strategic Implementation Framework",
        "FRAMEWORK",
        "image-left",
        (
            "Define a proprietary, named implementation framework for {topic} tailored to {audience}.\n"
            "RULES:\n"
            "  • The framework MUST have a unique name (e.g. 'The Precision Assembly Protocol', 'The Integrated Delivery Stack').\n"
            "  • Each phase must reference specific software, standards, or hardware by name.\n"
            "  • Include at least one quantified benchmark per phase.\n"
            "STRUCTURE:\n"
            "<p>Name the framework and explain its core philosophy in 2 sentences. State what makes it different from generic project management.</p>\n"
            "<h3>Phase 1: [Specific Technical Name]</h3>\n"
            "<p>Inputs, outputs, named tools/software, and measurable milestone. Tie to a {pain_points} resolution.</p>\n"
            "<h3>Phase 2: [Specific Technical Name]</h3>\n"
            "<p>Integration layer — how this phase connects upstream and downstream. Name the handoff protocol.</p>\n"
            "<h3>Phase 3: [Specific Technical Name]</h3>\n"
            "<p>Optimization — DFMA analysis, energy modelling, or performance benchmarking with a real metric.</p>\n"
            "<h3>When This Framework Fails</h3>\n"
            "<p>Name 2 specific conditions that break this framework and how to detect them early.</p>\n"
            "TARGET: 380–420 words. Named framework. No vague phases."
        )
    ),
    (
        "implementation_strategy",
        "High-Fidelity Implementation Roadmap",
        "IMPLEMENTATION",
        "text-only",
        (
            "Write a narrative implementation roadmap for {topic} — NOT a task list, but a story of how {audience} moves from current state to target state.\n"
            "RULES:\n"
            "  • Each phase must name the decision-maker, the tool or platform, and the deliverable.\n"
            "  • Include at least one risk mitigation per phase tied to {pain_points}.\n"
            "  • Use specific durations (e.g. 'Weeks 1–3', 'Day 30 checkpoint').\n"
            "STRUCTURE — 3 phases:\n"
            "<h3>Phase 1: [Technical Kickoff Name] — Weeks 1–4</h3>\n"
            "<p>Who does what, using which tools, producing which specific deliverable. Name the first decision gate.</p>\n"
            "<ul><li><strong>Milestone:</strong> [specific technical achievement]</li>"
            "<li><strong>Risk Mitigation:</strong> How to prevent a {pain_points} failure at this stage</li></ul>\n"
            "<h3>Phase 2: [Mid-Scale Integration Name] — Weeks 5–12</h3>\n"
            "<p>Narrative of integration — how data, teams, and systems connect. Name the handoff protocol.</p>\n"
            "<ul><li><strong>Milestone:</strong> [specific deliverable]</li>"
            "<li><strong>Risk Mitigation:</strong> Early warning indicator to watch</li></ul>\n"
            "<h3>Phase 3: [Steady-State Operations Name] — Month 4+</h3>\n"
            "<p>What 'normal operations' looks like, the metrics dashboard, and how {audience} knows it's working.</p>\n"
            "<ul><li><strong>Milestone:</strong> [performance benchmark achieved]</li>"
            "<li><strong>Risk Mitigation:</strong> How to course-correct if metrics slip</li></ul>\n"
            "TARGET: 380–420 words."
        )
    ),
    (
        "risk_management",
        "Institutional Risk Management",
        "RISK",
        "image-above",
        (
            "Identify 4 high-stakes, named risks specific to {topic} projects for {audience}.\n"
            "RULES:\n"
            "  • Each risk must have a technical name — not 'budget overrun' but 'Scope Creep from Unresolved RFIs'.\n"
            "  • Trigger must describe the exact workflow condition that causes the risk to activate.\n"
            "  • Mitigation must name a specific tool, protocol, or contractual clause.\n"
            "STRUCTURE — repeat 4 times:\n"
            "<h3>[Technical Risk Name]</h3>\n"
            "<p><strong>Trigger Condition:</strong> The specific moment in the {topic} workflow when this risk activates — name the phase, the actor, and the system.</p>\n"
            "<p><strong>Blast Radius:</strong> Quantified downstream impact — cost, time, or relationship damage with a realistic number.</p>\n"
            "<p><strong>Mitigation Protocol:</strong> Named tool, contractual mechanism, or process checkpoint that neutralises this risk before it propagates.</p>\n"
            "TARGET: 380–420 words. Four distinct risks. Hard technical language throughout."
        )
    ),
    (
        "best_practices",
        "Professional Standards & Best Practices",
        "METHODS",
        "text-only",
        (
            "Define 4 professional best practices for {audience} working in {topic}.\n"
            "RULES:\n"
            "  • Each practice must name a specific tool, platform, or published standard (e.g. Revit 2025, ISO 19650-2, Procore, AWS Wavelength).\n"
            "  • Each practice must include a specific performance metric — percentage improvement, time saved, error reduction rate.\n"
            "  • No vague advice like 'communicate clearly' or 'plan ahead'.\n"
            "STRUCTURE — repeat 4 times:\n"
            "<h3>[Practice Name — Action-Oriented]</h3>\n"
            "<p><strong>Method:</strong> Step-by-step implementation using [named tool/standard]. Be specific about configuration, frequency, or threshold.</p>\n"
            "<p><strong>Performance Benchmark:</strong> The specific, measurable improvement this delivers (e.g. '31% reduction in coordination RFIs', '2-week schedule compression per floor plate').</p>\n"
            "TARGET: 380–420 words. Four practices. Every claim backed by a number or named reference."
        )
    ),
    (
        "key_statistics",
        "Market Intelligence & Data Analysis",
        "DATA",
        "text-only",
        (
            "Provide a data-dense market intelligence section on {topic} for {audience}.\n"
            "RULES:\n"
            "  • Every statistic must include a source attribution (e.g. 'McKinsey Global Institute, 2024', 'Dodge Data & Analytics', 'RIBA Future Trends').\n"
            "  • Statistics must be specific — not 'costs are rising' but 'material cost inflation averaged 8.3% YoY in 2023–24 (Turner & Townsend)'.\n"
            "  • Include 3 comparative benchmarks showing the gap between leaders and laggards.\n"
            "STRUCTURE:\n"
            "<h3>Market Sizing & Growth Trajectory</h3>\n"
            "<p>3–4 specific data points with source attributions on the scale and growth of {topic}.</p>\n"
            "<h3>Performance Gap: Leaders vs. Laggards</h3>\n"
            "<ul>\n"
            "  <li><strong>[Metric 1]:</strong> Top quartile vs. industry average, with % delta and source.</li>\n"
            "  <li><strong>[Metric 2]:</strong> Time-to-delivery comparison with named methodology.</li>\n"
            "  <li><strong>[Metric 3]:</strong> Cost-per-unit delta between legacy and modern approaches.</li>\n"
            "</ul>\n"
            "<h3>Forward-Looking Indicators</h3>\n"
            "<p>2–3 projections or regulatory changes that will reshape {topic} within 36 months. Name the regulation or body.</p>\n"
            "TARGET: 380–420 words. Every number has a source or context. No made-up percentages without attribution."
        )
    ),
    (
        "process_steps",
        "Technical Workflow Stages",
        "PROCESS",
        "text-only",
        (
            "Map the complete technical workflow for implementing {topic}, written for {audience}.\n"
            "RULES:\n"
            "  • Use precise technical stage names — not 'Step 1: Planning' but 'Step 1: Parametric Schematic Design & Clash Pre-Check'.\n"
            "  • Each step must name the primary software or hardware used.\n"
            "  • Each step must name the specific deliverable and who receives it.\n"
            "STRUCTURE — 5 steps:\n"
            "<h3>Step 1: [Technical Stage Name]</h3>\n"
            "<p><strong>Inputs:</strong> What comes in. <strong>Tools:</strong> Named software/hardware. <strong>Output:</strong> Specific deliverable handed to [named role].</p>\n"
            "<h3>Step 2: [Technical Stage Name]</h3>\n"
            "<p>Same structure. Include a quality gate or tolerance specification.</p>\n"
            "<h3>Step 3: [Technical Stage Name]</h3>\n"
            "<p>Same structure. Name the coordination protocol used.</p>\n"
            "<h3>Step 4: [Technical Stage Name]</h3>\n"
            "<p>Same structure. Include a named compliance check or standard.</p>\n"
            "<h3>Step 5: [Technical Stage Name]</h3>\n"
            "<p>Same structure. Include a handover metric or sign-off criterion.</p>\n"
            "TARGET: 380–420 words. Five steps. Every step has a named tool and a named output."
        )
    ),
    (
        "comparison_table",
        "Strategic Comparative Analysis",
        "COMPARISON",
        "text-only",
        (
            "Write a head-to-head comparative analysis: traditional approaches vs {topic} for {audience}.\n"
            "RULES:\n"
            "  • Compare on 4 specific criteria — not 'speed' but 'design iteration cycle time'.\n"
            "  • Every comparison must include a number or named standard to anchor the delta.\n"
            "  • Write in a tone that makes the {audience} feel the urgency of switching — not evangelical, but data-driven.\n"
            "STRUCTURE:\n"
            "<p>One sharp opening sentence framing WHY this comparison matters now for {audience}.</p>\n"
            "<h3>Criteria 1: [Specific Technical Metric]</h3>\n"
            "<p>Traditional: [specific outcome with number]. {topic} approach: [specific outcome with number]. Net delta: [X%] advantage, source or benchmark.</p>\n"
            "<h3>Criteria 2: [Financial Performance Metric]</h3>\n"
            "<p>Same pattern. Focus on the {pain_points} most relevant to cost or schedule.</p>\n"
            "<h3>Criteria 3: [Quality or Compliance Metric]</h3>\n"
            "<p>Same pattern. Name the standard or defect rate being compared.</p>\n"
            "<h3>Criteria 4: [Lifecycle or Risk Metric]</h3>\n"
            "<p>Same pattern. Include maintenance cost or operational performance delta.</p>\n"
            "TARGET: 380–420 words. Four criteria. Every claim is anchored."
        )
    ),
    (
        "key_takeaways",
        "Strategic Takeaways & Next Moves",
        "TAKEAWAYS",
        "text-only",
        (
            "Summarise the 3 most important strategic pivots {audience} must make to win in {topic}.\n"
            "RULES:\n"
            "  • Each takeaway must be a named pivot — not 'adopt BIM' but 'Shift from Drawing-Centric to Data-Centric Coordination'.\n"
            "  • Each must include one specific action {audience} can take in the next 30 days.\n"
            "  • End with a high-urgency closing paragraph — no vague optimism, just a specific threat or opportunity.\n"
            "STRUCTURE — 3 pivots:\n"
            "<h3>Pivot 1: [Named Strategic Shift]</h3>\n"
            "<p>Why this pivot is non-negotiable now. Name the force (regulatory, competitive, financial) driving it. 3–4 sentences.</p>\n"
            "<ul><li><strong>30-Day Action:</strong> One specific, implementable step with a named tool or partner.</li>"
            "<li><strong>Success Signal:</strong> How {audience} knows this pivot is working.</li></ul>\n"
            "<h3>Pivot 2: [Named Strategic Shift]</h3>\n"
            "<p>Same structure. Focus on a different dimension of {topic}.</p>\n"
            "<ul><li><strong>30-Day Action:</strong> ...</li><li><strong>Success Signal:</strong> ...</li></ul>\n"
            "<h3>Pivot 3: [Named Strategic Shift]</h3>\n"
            "<p>Same structure.</p>\n"
            "<ul><li><strong>30-Day Action:</strong> ...</li><li><strong>Success Signal:</strong> ...</li></ul>\n"
            "<p><strong>The Window:</strong> A closing paragraph naming the specific timeline or market event that makes delay costly.</p>\n"
            "TARGET: 380–420 words."
        )
    ),
    (
        "conclusion",
        "Conclusion & 90-Day Activation Roadmap",
        "CONCLUSION",
        "text-only",
        (
            "Write the conclusion and a concrete 90-day activation plan for {audience} to implement {topic}.\n"
            "RULES:\n"
            "  • The conclusion must name the single biggest ROI argument for {topic} — with a number.\n"
            "  • The 90-day plan must have named deliverables, not vague milestones.\n"
            "  • The CTA must be specific — not 'contact us' but 'Book a 45-minute {topic} Readiness Audit'.\n"
            "STRUCTURE:\n"
            "<p>2–3 sentences: The core value proposition of acting now on {topic}, with the strongest ROI stat from this guide.</p>\n"
            "<h3>Your 90-Day {topic} Activation Roadmap</h3>\n"
            "<ol>\n"
            "  <li><strong>Days 1–30 — Diagnostic:</strong> Named audit, named tool, specific output (e.g. 'A gap analysis report against ISO 19650 requirements').</li>\n"
            "  <li><strong>Days 31–60 — Pilot:</strong> Specific pilot scope, named software, measurable success criterion.</li>\n"
            "  <li><strong>Days 61–90 — Scale:</strong> How to expand from pilot to full deployment. Named metric that triggers scale decision.</li>\n"
            "</ol>\n"
            "<h3>Your Next Step</h3>\n"
            "<p>A specific, named CTA — not generic. Tell {audience} exactly what they get, how long it takes, and what happens next.</p>\n"
            "TARGET: 280–320 words. Specific. Actionable. No waffle."
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

ALLOWED_TAGS = {"p", "strong", "em", "h3", "h4", "ul", "ol", "li", "br", "blockquote", "footer"}

# ─────────────────────────────────────────────────────────────────────────────
# FILLER DETECTION — strip AI boilerplate before it reaches the template
# ─────────────────────────────────────────────────────────────────────────────
_FILLER_PATTERNS = [
    r"this (section|guide|document|report) (provides?|offers?|explores?|covers?|aims? to|is designed to)",
    r"in (today's|the current|this) (fast[- ]paced|rapidly changing|evolving|dynamic|competitive)",
    r"it is (important|crucial|essential|critical) (to note|to understand|that)",
    r"(as we|let us|let's) (explore|delve|dive|look at|examine)",
    r"(understanding|navigating) the (complexities|nuances|intricacies) of",
    r"(the following|below) (section|content|information) (will|provides?|outlines?)",
    r"in conclusion,? (this|it|we)",
    r"(to summarize|in summary|to recap),",
    r"this comprehensive (guide|report|document)",
    r"(by the end of this|after reading this)",
]

_FILLER_RE = re.compile("|".join(_FILLER_PATTERNS), re.IGNORECASE)


def _strip_filler(html: str) -> str:
    """Remove AI boilerplate sentence openers from generated HTML."""
    if not html:
        return html
    # Remove filler sentences (sentence ending with period/exclamation)
    sentences = re.split(r'(?<=[.!?])\s+', html)
    cleaned = []
    for sentence in sentences:
        if _FILLER_RE.search(sentence):
            logger.debug(f"Stripped filler: {sentence[:80]}")
            continue
        cleaned.append(sentence)
    return " ".join(cleaned)


def _deduplicate_content(html: str) -> str:
    """Remove duplicate sentences that appear more than once."""
    if not html:
        return html
    seen = set()
    result = []
    # Split on sentence boundaries while preserving tags
    parts = re.split(r'(<[^>]+>)', html)
    for part in parts:
        if part.startswith('<'):
            result.append(part)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', part)
            unique = []
            for s in sentences:
                norm = re.sub(r'\s+', ' ', s.strip().lower())
                if norm and norm not in seen:
                    seen.add(norm)
                    unique.append(s)
            result.append(' '.join(unique))
    return ''.join(result)


class GroqClient:
    SECTIONS = SECTIONS
    DOC_TYPE_LABELS = DOC_TYPE_LABELS
    _TYPE_MAP = _TYPE_MAP
    SECTION_LAYOUT = {key: layout for key, _, _, layout, _ in SECTIONS}

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")
        self.client      = Groq(api_key=api_key)
        self.model       = "llama-3.3-70b-versatile"
        self.temperature = 0.55          # slightly higher for variation
        self.max_tokens  = 4096
        self._analysis   = None
        self._framework  = None

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────

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
            "tone":            user_answers.get("tone", "Institutional and Professional"),
            "industry":        user_answers.get("industry", "Architecture and Design"),
            "document_type":   doc_type,
        }

    def generate_lead_magnet_json(self, signals: Dict[str, Any], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        doc_type   = signals.get("document_type", "guide")
        type_label = DOC_TYPE_LABELS.get(doc_type) or DOC_TYPE_LABELS["guide"]
        logger.info(f"📄 {type_label} | topic={signals['topic']} | model={self.model}")

        logger.info("🧠 Layer 1 — Input Analysis")
        self._analysis = self._analyze_inputs(signals)

        logger.info("📐 Layer 2 — Framework Generation")
        section_keys = [key for key, _, _, _, _ in SECTIONS]
        self._framework = self._generate_framework(self._analysis, section_keys, signals)

        title_data = self._generate_title(signals, type_label)
        expansions: Dict[str, str] = {}
        for key, title, label, _layout, brief in SECTIONS:
            logger.info(f"✍️  Layer 3 — {key}")
            expansions[key] = self._generate_section(key, title, brief, signals)

        framework_data = self._framework.get("sections", {})
        self._analysis  = None
        self._framework = None

        return {
            "title":                   title_data.get("title", signals["topic"]),
            "subtitle":                title_data.get("subtitle", type_label),
            "target_audience_summary": title_data.get("target_audience_summary", ""),
            "legal_notice_summary":    title_data.get("legal_notice_summary", ""),
            "cta_headline":            title_data.get("cta_headline", ""),
            "cta_text":                title_data.get("cta_text", ""),
            "document_type":           doc_type,
            "document_type_label":     type_label,
            "expansions":              expansions,
            "framework":               framework_data,
        }

    def normalize_ai_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        exp = raw.get("expansions", {})
        fw  = raw.get("framework", {})
        normalized: Dict[str, Any] = {
            "title":                raw.get("title") or "",
            "subtitle":             raw.get("subtitle", ""),
            "summary":              raw.get("target_audience_summary", ""),
            "legal_notice_summary": raw.get("legal_notice_summary", ""),
            "cta_headline":         raw.get("cta_headline", ""),
            "cta_text":             raw.get("cta_text", ""),
            "document_type":        raw.get("document_type", "guide"),
            "document_type_label":  raw.get("document_type_label") or "",
            "sections_config":      self.SECTIONS,
            "framework":            fw,
        }
        for key, *_ in SECTIONS:
            content = exp.get(key, "")
            if isinstance(content, dict):
                content = json.dumps(content)

            raw_html  = content if isinstance(content, str) else str(content)
            sanitized = self._sanitize_html(raw_html)
            sanitized = _strip_filler(sanitized)
            sanitized = _deduplicate_content(sanitized)
            normalized[key] = sanitized

            if key == "key_statistics":
                self._extract_stats(sanitized, normalized)
            elif key == "process_steps":
                self._extract_steps(sanitized, normalized)
            elif key == "comparison_table":
                self._extract_table(sanitized, normalized)
            elif key == "key_takeaways":
                self._extract_icons(sanitized, normalized)
            elif key == "implementation_strategy":
                self._extract_timeline(sanitized, normalized)
            elif key == "best_practices":
                self._extract_checklists(sanitized, normalized, "extListItem", 6)
            elif key == "key_challenges":
                self._extract_checklists(sanitized, normalized, "listItem", 4)
            elif key == "risk_management":
                self._extract_checklists(sanitized, normalized, "numberedItem", 4)
                self._extract_quote(sanitized, normalized, 2)
            elif key == "conclusion":
                self._extract_cta(sanitized, normalized)

        return normalized

    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Dict[str, Any],
        signals: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        signals = signals or {}

        # ── Colours ───────────────────────────────────────────────────────────
        primary_color = (
            firm_profile.get("primary_brand_color")
            or signals.get("primary_color")
            or "#1a365d"
        )
        if not str(primary_color).startswith("#"):
            primary_color = "#" + primary_color

        secondary_color = firm_profile.get("secondary_brand_color") or "#c5a059"
        if not str(secondary_color).startswith("#"):
            secondary_color = "#" + secondary_color

        accent_color = firm_profile.get("accent_color") or "#f8fafc"
        if not str(accent_color).startswith("#"):
            accent_color = "#" + accent_color

        highlight_color = firm_profile.get("highlight_color") or "#e8f4f8"
        gold_color      = firm_profile.get("gold_color") or "#c5a059"

        # ── Company info ──────────────────────────────────────────────────────
        company_name = (
            firm_profile.get("firm_name")
            or firm_profile.get("name")
            or (signals.get("topic") if signals else "Strategic Analysis")
        )
        topic = signals.get("topic", "Industry Best Practices")

        # ── Core vars ─────────────────────────────────────────────────────────
        vars: Dict[str, Any] = {
            "documentTitle":     ai_content.get("title") or topic,
            "primaryColor":      primary_color,
            "secondaryColor":    secondary_color,
            "accentColor":       accent_color,
            "highlightColor":    highlight_color,
            "goldColor":         gold_color,
            "documentTypeLabel": ai_content.get("document_type_label") or "STRATEGIC GUIDE",
            "mainTitle":         ai_content.get("title") or topic,
            "mainTitleAccent":   ai_content.get("subtitle") or "",
            "documentSubtitle":  ai_content.get("subtitle") or f"A practitioner's guide to {topic}.",
            "companyName":       company_name,
            "companySubtitle":   firm_profile.get("company_subtitle", ""),
            "emailAddress":      firm_profile.get("work_email", ""),
            "phoneNumber":       firm_profile.get("phone_number", ""),
            "website":           firm_profile.get("firm_website", ""),
            "logoPlaceholder":   company_name[:2].upper() if company_name else "AI",
            "footerText":        f"© {company_name} — Confidential",
            "differentiator":    (
                firm_profile.get("branding_guidelines")
                or f"Proven specialists in {topic} with a track record of measurable results."
            ),
        }

        # ── Terms of use (page 2) — fully dynamic ─────────────────────────────
        legal = ai_content.get("legal_notice_summary") or (
            f"This {ai_content.get('document_type_label','guide')} on {topic} is provided for "
            f"informational and strategic guidance purposes only."
        )
        vars.update({
            "termsTitle":      "Terms of Use & Disclaimer",
            "termsSummary":    legal,
            "termsParagraph1": f"© {company_name}. All rights reserved. Unauthorised reproduction or distribution is prohibited.",
            "termsParagraph2": (
                f"The information in this document relates to {topic} and reflects the state of "
                f"the industry as of the date of publication. It does not constitute legal, financial, or professional advice."
            ),
            "termsParagraph3": (
                "Given the dynamic nature of regulations, technology, and market conditions, readers are advised "
                "to verify all information independently before making business decisions."
            ),
            "termsParagraph4": (
                f"While every effort has been made to ensure accuracy, {company_name} accepts no liability "
                "for errors, omissions, or outcomes arising from the use of this material."
            ),
            "termsParagraph5": (
                f"This document was produced using AI-assisted research and editorial tools. "
                f"All strategic recommendations should be validated by a qualified {signals.get('industry','industry')} professional."
            ),
        })

        # ── Table of contents (page 3) ─────────────────────────────────────────
        fw = ai_content.get("framework", {})
        toc_page = 4
        for idx, (key, default_title, default_label, _, _) in enumerate(SECTIONS):
            sec_fw     = fw.get(key, {})
            sec_title  = sec_fw.get("title") or default_title
            sec_label  = sec_fw.get("kicker") or default_label
            s_idx      = idx + 1

            vars[f"sectionTitle{idx+3}"] = sec_label
            vars[f"contentItem{s_idx}"]  = sec_title
            vars[f"pageNumber{toc_page}"] = str(toc_page).zfill(2)
            toc_page += 1

        # Alias for header slots (pages 2–9 headers)
        vars["sectionTitle1"] = "TERMS OF USE"
        vars["sectionTitle2"] = "CONTENTS"
        vars["pageNumberHeader2"] = "02"
        vars["pageNumberHeader3"] = "03"
        for i in range(4, 15):
            vars[f"pageNumberHeader{i}"] = str(i).zfill(2)

        vars["contentsTitle"] = "Table of Contents"

        # ── Section content vars ───────────────────────────────────────────────
        for idx, (key, default_title, default_label, _, _) in enumerate(SECTIONS):
            sec_fw    = fw.get(key, {})
            sec_title = sec_fw.get("title") or default_title
            content   = ai_content.get(key, "")
            s_idx     = idx + 1

            vars[f"customTitle{s_idx}"]   = sec_title
            vars[f"customContent{s_idx}"] = self._extract_intro(content)

            subheadings = self._extract_subheadings(content)
            if subheadings:
                vars[f"subheading{s_idx}"]  = subheadings[0]
                vars[f"subcontent{s_idx}"]  = self._extract_subcontent(content, subheadings[0])
            else:
                vars[f"subheading{s_idx}"]  = sec_title
                vars[f"subcontent{s_idx}"]  = content[:300] if content else ""

            boxes = self._extract_boxes(content)
            if boxes:
                vars[f"boxTitle{s_idx}"]   = boxes[0][0]
                vars[f"boxContent{s_idx}"] = boxes[0][1]
            else:
                vars[f"boxTitle{s_idx}"]   = sec_title
                vars[f"boxContent{s_idx}"] = self._extract_intro(content)

            # Populate checklist items per section
            items = re.findall(r'<li>(.*?)</li>', content, re.S)
            for li_idx, item in enumerate(items[:6]):
                vars[f"listItem{s_idx}_{li_idx+1}"] = item

        # ── Flat list/checklist vars (template legacy slots) ──────────────────
        # Pull from key_challenges for listItem1–4
        challenges_content = ai_content.get("key_challenges", "")
        ch_items = re.findall(r'<li>(.*?)</li>', challenges_content, re.S)
        for i, item in enumerate(ch_items[:4]):
            vars[f"listItem{i+1}"] = item

        # Pull from best_practices for extListItem1–6
        bp_content = ai_content.get("best_practices", "")
        bp_items = re.findall(r'<li>(.*?)</li>', bp_content, re.S)
        for i, item in enumerate(bp_items[:6]):
            vars[f"extListItem{i+1}"] = item

        # Pull from risk_management for numberedItem1–4
        risk_content = ai_content.get("risk_management", "")
        risk_items = re.findall(r'<li>(.*?)</li>', risk_content, re.S)
        for i, item in enumerate(risk_items[:4]):
            vars[f"numberedItem{i+1}"] = item

        # ── Stats from key_statistics ──────────────────────────────────────────
        stats_content = ai_content.get("key_statistics", "")
        stat_items = re.findall(r'<li><strong>(.*?)</strong>\s*:?\s*(.*?)</li>', stats_content, re.S)
        for i, (lbl, val) in enumerate(stat_items[:3]):
            vars[f"stat{i+1}Label"] = lbl.strip()
            vars[f"stat{i+1}Value"] = val.strip()

        # ── Steps from process_steps ───────────────────────────────────────────
        steps_content = ai_content.get("process_steps", "")
        step_matches  = re.findall(r'<h3>Step \d+:\s*(.*?)</h3>\s*<p>(.*?)</p>', steps_content, re.S)
        for i, (title, body) in enumerate(step_matches[:5]):
            vars[f"stepTitle{i+1}"]   = title.strip()
            vars[f"stepContent{i+1}"] = re.sub(r'<[^>]+>', '', body).strip()[:200]

        # ── Takeaway icon cards ────────────────────────────────────────────────
        takeaway_content = ai_content.get("key_takeaways", "")
        pivots = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', takeaway_content, re.S)
        for i, (title, body) in enumerate(pivots[:4]):
            vars[f"iconCard{i+1}Title"] = title.strip()
            clean_body = re.sub(r'<[^>]+>', '', body).strip()
            vars[f"iconCard{i+1}Text"]  = clean_body[:120] + ("..." if len(clean_body) > 120 else "")

        # ── Timeline from implementation_strategy ─────────────────────────────
        impl_content = ai_content.get("implementation_strategy", "")
        phases = re.findall(r'<h3>Phase \d+:\s*(.*?)</h3>\s*<p>(.*?)</p>', impl_content, re.S)
        for i, (title, body) in enumerate(phases[:5]):
            vars[f"timelineItem{i+1}Title"] = title.strip()
            vars[f"timelineItem{i+1}"]      = re.sub(r'<[^>]+>', '', body).strip()[:200]

        # ── CTA / Contact page vars ────────────────────────────────────────────
        cta_headline = (
            ai_content.get("cta_headline")
            or f"Ready to Transform Your {topic} Outcomes?"
        )
        cta_text_raw = ai_content.get("cta_text") or ""
        # Strip generic CTAs and replace with specific ones
        if not cta_text_raw or re.search(r'contact (us|kyro|me) today', cta_text_raw, re.I):
            cta_text_raw = (
                f"Book a complimentary 45-minute {topic} Readiness Audit with our team. "
                f"You'll leave with a prioritised action plan, a gap analysis against current "
                f"industry benchmarks, and a clear ROI projection — no obligation."
            )

        vars.update({
            "ctaHeadline":         cta_headline,
            "ctaText":             cta_text_raw,
            "ctaText2":            cta_text_raw,
            "ctaButtonText":       f"Book Your {topic} Audit →",
            "ctaText":             cta_text_raw,
            "differentiatorTitle": "Why Work With Us",
            "contactDescription":  cta_text_raw,
        })

        # ── Architectural image captions ───────────────────────────────────────
        for i in range(1, 7):
            vars[f"architecturalImageCaption{i}"] = f"{topic} — Project Reference {i}"
            vars[f"image_{i}_url"]                = firm_profile.get(f"image_{i}_url", "")
            vars[f"image_{i}_caption"]            = firm_profile.get(f"image_{i}_caption", f"Project Insight {i}")

        # ── Column box vars (page 7) ──────────────────────────────────────────
        vars["columnBoxTitle1"] = "Detail View"
        vars["columnBoxContent1"] = self._extract_intro(ai_content.get("process_steps", ""))

        # ── Info/accent boxes ──────────────────────────────────────────────────
        vars["accentBoxTitle3"]   = "Key Insight"
        vars["accentBoxContent3"] = self._extract_intro(ai_content.get("risk_management", ""))

        # ── Quote vars ─────────────────────────────────────────────────────────
        # Pull real quotes from content if present, otherwise build from data
        for q_idx in range(1, 4):
            if not vars.get(f"quoteText{q_idx}"):
                vars[f"quoteText{q_idx}"]   = ""
            if not vars.get(f"quoteAuthor{q_idx}"):
                vars[f"quoteAuthor{q_idx}"] = "Industry Analysis"

        # ── Image caption keys referenced in template ──────────────────────────
        vars["architecturalImageCaption1"] = f"{topic} — Execution Detail"
        vars["architecturalImageCaption2"] = f"{topic} — Technical Overview"
        vars["architecturalImageCaption3"] = f"{topic} — Process View"

        # ── Pass full section HTML through for any template that renders it ───
        for key, *_ in SECTIONS:
            vars[f"section_{key}_html"] = ai_content.get(key, "")

        # ── Merge remaining ai_content fields (except already-mapped top-level) ──
        skip = {"title", "subtitle", "summary", "document_type", "document_type_label",
                "sections_config", "expansions", "framework"}
        for k, v in ai_content.items():
            if k not in skip and k not in vars:
                vars[k] = v

        # ── Page numbers (legacy compat) ───────────────────────────────────────
        for n in range(2, 16):
            vars[f"pageNumber{n}"] = str(n).zfill(2)

        return vars

    # ─────────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────────────────

    def _extract_intro(self, html: str) -> str:
        match = re.search(r'<p>(.*?)</p>', html, re.S)
        return re.sub(r'<[^>]+>', '', match.group(1)).strip() if match else ""

    def _extract_subheadings(self, html: str) -> List[str]:
        return re.findall(r'<h3>(.*?)</h3>', html)

    def _extract_subcontent(self, html: str, subheading: str) -> str:
        pattern = rf'<h3>{re.escape(subheading)}</h3>\s*(.*?)(?:<h3>|$)'
        match   = re.search(pattern, html, re.S)
        if not match:
            return ""
        raw = match.group(1).strip()
        return re.sub(r'<[^>]+>', '', raw).strip()[:400]

    def _extract_boxes(self, html: str) -> List[tuple]:
        matches = re.findall(r'<h3>(.*?)</h3>\s*(<p>.*?</p>|<ul>.*?</ul>)', html, re.S)
        return [(m[0], re.sub(r'<[^>]+>', '', m[1]).strip()) for m in matches]

    def _extract_stats(self, html: str, data: Dict):
        vals = re.findall(r'<li><strong>(.*?)</strong>\s*:?\s*(.*?)</li>', html, re.S)
        for i, (lbl, val) in enumerate(vals):
            if i < 3:
                data[f"stat{i+1}Value"] = re.sub(r'<[^>]+>', '', val).strip()
                data[f"stat{i+1}Label"] = re.sub(r'<[^>]+>', '', lbl).strip()

    def _extract_steps(self, html: str, data: Dict):
        steps = re.findall(r'<h3>Step \d+:\s*(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(steps):
            if i < 5:
                data[f"stepTitle{i+1}"]   = ttl.strip()
                data[f"stepContent{i+1}"] = re.sub(r'<[^>]+>', '', cnt).strip()

    def _extract_table(self, html: str, data: Dict):
        criteria = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(criteria):
            if i < 4:
                data[f"tableRow{i+1}Col1"] = ttl.strip()
                data[f"tableRow{i+1}Col2"] = re.sub(r'<[^>]+>', '', cnt).strip()[:150]

    def _extract_icons(self, html: str, data: Dict):
        themes = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(themes):
            if i < 4:
                clean = re.sub(r'<[^>]+>', '', cnt).strip()
                data[f"iconCard{i+1}Title"] = ttl.strip()
                data[f"iconCard{i+1}Text"]  = clean[:100] + ("..." if len(clean) > 100 else "")

    def _extract_timeline(self, html: str, data: Dict):
        phases = re.findall(r'<h3>Phase \d+:\s*(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(phases):
            if i < 5:
                data[f"timelineItem{i+1}Title"] = ttl.strip()
                data[f"timelineItem{i+1}"]      = re.sub(r'<[^>]+>', '', cnt).strip()

    def _extract_checklists(self, html: str, data: Dict, prefix: str, limit: int):
        items = re.findall(r'<li>(.*?)</li>', html, re.S)
        for i, itm in enumerate(items):
            if i < limit:
                data[f"{prefix}{i+1}"] = re.sub(r'<[^>]+>', '', itm).strip()

    def _extract_quote(self, html: str, data: Dict, idx: int):
        match = re.search(r'<blockquote>(.*?)</blockquote>', html, re.S)
        if match:
            data[f"quoteText{idx}"]   = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            data[f"quoteAuthor{idx}"] = "Industry Strategic Analysis"

    def _extract_cta(self, html: str, data: Dict):
        match = re.search(r'<h3>(.*?)</h3>', html)
        if match:
            data["ctaHeadline"] = match.group(1).strip()

    # ─────────────────────────────────────────────────────────────────────
    # AI LAYERS
    # ─────────────────────────────────────────────────────────────────────

    def _analyze_inputs(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        system = (
            "You are a domain expert and institutional strategist. "
            "Your output feeds an AI content pipeline — be specific, technical, and zero-filler. "
            "Return valid JSON only. No markdown. No prose."
        )
        prompt = (
            f"Analyze these inputs and return structured domain intelligence for a professional guide.\n\n"
            f"Topic: {signals['topic']}\n"
            f"Audience: {signals['audience']}\n"
            f"Pain Points: {signals['pain_points']}\n"
            f"Industry: {signals.get('industry', 'Architecture')}\n\n"
            f"Return ONLY this JSON (be specific — name real tools, standards, metrics):\n"
            f"{{\n"
            f"  \"industry_context\": \"2–3 sentences on the current technical and market state of this industry, with a specific stat or standard\",\n"
            f"  \"core_problem_summary\": \"The precise technical/process failure that underlies these pain points\",\n"
            f"  \"stakeholder_roles\": [\"specific role 1\", \"specific role 2\", \"specific role 3\"],\n"
            f"  \"strategic_focus_areas\": [\"named focus 1\", \"named focus 2\", \"named focus 3\"],\n"
            f"  \"risk_factors\": [\"named technical risk 1\", \"named technical risk 2\"],\n"
            f"  \"pain_point_solutions\": {{ \"pain point key\": \"named solution/framework\" }},\n"
            f"  \"implementation_priorities\": [\"priority 1 with tool name\", \"priority 2 with metric\"]\n"
            f"}}"
        )
        return self._call_ai(system, prompt, max_tokens=600)

    def _generate_framework(
        self, analysis: Dict[str, Any], section_keys: List[str], signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        system = (
            "You are a senior content strategist for institutional professional guides. "
            "Every title and kicker must be domain-specific and action-oriented — no generic labels. "
            "Return valid JSON only. No markdown."
        )
        keys_str = json.dumps(section_keys)
        prompt = (
            f"Create a content framework plan for a professional guide on {signals['topic']} for {signals['audience']}.\n"
            f"DOMAIN CONTEXT: {json.dumps(analysis)}\n\n"
            f"For EACH section key in {keys_str}, return an object with:\n"
            f"  title: A 4–6 word, domain-specific, action-oriented heading (NOT generic)\n"
            f"  kicker: 1 uppercase word that labels this section's function\n"
            f"  angle: 1 sentence — what specific insight or argument does this section make?\n"
            f"  key_points: exactly 3 specific, technical points this section must make\n"
            f"  pain_point_tie: which specific pain point from [{signals['pain_points']}] this resolves\n\n"
            f"Return ONLY: {{\"sections\": {{ \"section_key\": {{\"title\":\"...\",\"kicker\":\"...\",\"angle\":\"...\",\"key_points\":[...],\"pain_point_tie\":\"...\"}} }} }}"
        )
        result = self._call_ai(system, prompt, max_tokens=2000)
        if "sections" not in result and isinstance(result, dict):
            result = {"sections": result}
        return result

    def _generate_title(self, signals: Dict, type_label: str) -> Dict:
        system = (
            "You are a senior document strategist. Titles must be specific to the topic — no generic phrases. "
            "CTAs must name what the reader gets, not just say 'contact us'. "
            "Return valid JSON only. No markdown."
        )
        prompt = (
            f"Generate metadata for a {type_label} on: {signals['topic']} for {signals['audience']}.\n"
            f"Pain points being addressed: {signals['pain_points']}\n\n"
            f"Rules:\n"
            f"  - title: 6–10 words, specific to {signals['topic']}, not generic\n"
            f"  - subtitle: 10–15 words explaining the specific value of this guide\n"
            f"  - cta_headline: a question or statement that names the specific transformation available\n"
            f"  - cta_text: 2 sentences — what the reader gets from booking/downloading, with a named deliverable\n"
            f"  - legal_notice_summary: 1 sentence legal disclaimer specific to {signals['industry']} advice\n\n"
            f"Return ONLY: {{\"title\":\"...\",\"subtitle\":\"...\",\"target_audience_summary\":\"...\","
            f"\"legal_notice_summary\":\"...\",\"cta_headline\":\"...\",\"cta_text\":\"...\"}}"
        )
        return self._call_ai(system, prompt, max_tokens=500)

    def _generate_section(self, key: str, title: str, brief: str, signals: Dict) -> str:
        brief_filled = brief.format(
            topic       = signals["topic"],
            audience    = signals["audience"],
            pain_points = signals["pain_points"],
            industry    = signals.get("industry") or signals["topic"],
        )
        analysis = self._analysis or {}
        secs     = (self._framework or {}).get("sections", {})
        sec_plan = secs.get(key, {})
        key_pts  = sec_plan.get("key_points", [])
        angle    = sec_plan.get("angle", "")

        system = (
            f"You are a domain expert and senior consultant in {signals['topic']} writing for {signals['audience']}.\n"
            f"You are writing ONE section of a premium institutional professional guide.\n\n"
            f"INDUSTRY CONTEXT: {analysis.get('industry_context', '')}\n"
            f"CORE PROBLEM THIS GUIDE SOLVES: {analysis.get('core_problem_summary', '')}\n"
            f"THIS SECTION'S ANGLE: {angle}\n"
            f"KEY POINTS TO MAKE: {json.dumps(key_pts)}\n\n"
            f"ABSOLUTE RULES — violating any of these FAILS the section:\n"
            f"  1. NEVER open with 'This section', 'This guide', 'In today's world', or any meta-phrase.\n"
            f"  2. Every paragraph must include at least ONE specific metric, tool name, or standard.\n"
            f"  3. No filler sentences — every sentence must add new information.\n"
            f"  4. No repetition — if a point is made once, don't restate it.\n"
            f"  5. Write like a practitioner talking to a peer — authoritative, not academic.\n"
            f"  6. Allowed HTML only: <p> <strong> <em> <h3> <h4> <ul> <ol> <li> <br> <blockquote> <footer>\n"
            f"  7. Do NOT include a title/heading at the top — section starts immediately with content.\n"
            f"  8. Return valid JSON: {{\"{key}\": \"HTML string\"}} ONLY.\n"
        )
        prompt = (
            f"Write the '{title}' section.\n"
            f"BRIEF:\n{brief_filled}\n\n"
            f"Return ONLY: {{\"{key}\": \"<HTML content here>\"}}"
        )
        raw = self._call_ai(system, prompt, max_tokens=2000)
        return self._sanitize_html(self._extract_content(raw, key))

    # ─────────────────────────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────────────────────────

    def _extract_content(self, result: Dict, key: str) -> str:
        if not result:
            return ""
        if key in result and isinstance(result[key], str):
            return result[key]
        # Fallback: find the longest string value
        best = ""
        for k, v in result.items():
            if isinstance(v, str) and len(v) > len(best):
                best = v
        return best

    def _sanitize_html(self, html: str) -> str:
        if not html:
            return html
        html = html.strip().strip('"')
        # Remove disallowed tags but keep content
        def _replace_tag(m):
            tag = m.group(2).lower()
            if tag in ALLOWED_TAGS:
                return m.group(0)
            # Keep text content, drop tag
            return ""
        html = re.sub(r'<(/?)(\w+)([^>]*)>', _replace_tag, html)
        return self._ensure_closed_tags(html).strip()

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model           = self.model,
                messages        = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature     = self.temperature,
                max_tokens      = max_tokens or self.max_tokens,
                response_format = {"type": "json_object"},
            )
            raw_text = response.choices[0].message.content
            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            raise RuntimeError(f"Groq API failed: {e}")

    def _ensure_closed_tags(self, html: str) -> str:
        void  = {"br", "hr", "img", "input", "link", "meta"}
        tags  = re.findall(r"<(/?)([a-zA-Z1-6]+)", html)
        stack = []
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

    # ── Stub kept for backward compat with FormaAIConversationView ────────────
    def ensure_section_content(
        self, sections: list, signals: Dict[str, Any], firm_profile: Dict[str, Any]
    ) -> list:
        """Pass-through — sections are now always generated in generate_lead_magnet_json."""
        return sections
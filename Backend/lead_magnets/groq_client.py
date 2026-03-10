import os
import json
import logging
import time
import re
import traceback as _tb
from typing import Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)

SECTIONS = [
    (
        "executive_summary",
        "Strategic Executive Overview",
        "OVERVIEW",
        "text-only",
        (
            "Write a high-level Strategic Executive Overview for a professional guide on {topic} for {audience}.\n"
            "The tone must be authoritative, strategic, and institutional.\n"
            "REQUIRED: Use at least 3 specific industry metrics with context (e.g. 'average lifecycle cost reduction of 18% in LGSF projects').\n"
            "STRUCTURE:\n"
            "<p> — 4-5 sentences: A compelling overview of what {topic} means for {audience} and why it's critical NOW.\n"
            "<h3>Strategic Market Drivers</h3>\n"
            "<p>Analyze the macroeconomic or industry-specific forces driving this shift.</p>\n"
            "<ul> — 4 specific drivers linked to the pain points: {pain_points}. Use <strong> for technical terms.\n"
            "<p> — A powerful closing statement on the expected long-term strategic outcome.\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "key_challenges",
        "Critical Industry Challenges",
        "CHALLENGES",
        "image-right",
        (
            "Identify the most critical technical and operational challenges for {audience} in {topic}.\n"
            "REQUIRED: Name specific failure modes (e.g. 'BIM data siloed in Revit 2024') and technical blockers.\n"
            "STRUCTURE — for EACH pain point in [{pain_points}]:\n"
            "<h3>[Challenge Name]</h3>\n"
            "<p><strong>Technical Root Cause:</strong> Explain the underlying software/mechanical reason this occurs.</p>\n"
            "<p><strong>Operational Impact:</strong> Describe the downstream cost or delay using specific metrics.</p>\n"
            "<p><strong>Strategic Resolution:</strong> A realistic industry situation where this challenge disrupts the workflow.</p>\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "strategic_framework",
        "Strategic Implementation Framework",
        "FRAMEWORK",
        "image-left",
        (
            "Define a comprehensive Strategic Framework for {topic} tailored to {audience}.\n"
            "REQUIRED: Name a unique, proprietary-sounding framework (e.g. 'The Modular Synthesis Protocol').\n"
            "STRUCTURE:\n"
            "<p> — An introduction to the framework's methodology and philosophy.</p>\n"
            "<h3>[Phase 1: Domain-Specific Name]</h3>\n"
            "<p> — Actionable details: what practitioners DO, naming specific software (e.g. Procore, Autodesk Construction Cloud) or hardware.</p>\n"
            "<h3>[Phase 2: Technical Integration]</h3>\n"
            "<p> — How it resolves one of [{pain_points}]. Use a real-world metric or benchmark.</p>\n"
            "<h3>[Phase 3: Optimization]</h3>\n"
            "<p> — Advanced optimization (e.g. 'DFMA analysis', 'carbon sequestration metrics').</p>\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "implementation_strategy",
        "High-Fidelity Roadmap",
        "IMPLEMENTATION",
        "text-only",
        (
            "Provide a high-fidelity Implementation Strategy for {topic}.\n"
            "REQUIRED: This must be a narrative roadmap, NOT just a list of tasks. Connect actions to long-term outcomes.\n"
            "STRUCTURE — 3 Phases, each with <h3> + narrative <p> + <ul>:\n"
            "<h3>Phase 1: [Technical Kickoff Name]</h3>\n"
            "<p>Detail the kickoff requirements in 4-5 sentences, referencing specific {topic} standards or protocols.</p>\n"
            "<ul>\n"
            "  <li><strong>Milestone:</strong> A specific technical achievement.</li>\n"
            "  <li><strong>Risk Factor:</strong> How to proactively mitigate a [{pain_points}] failure at this stage.</li>\n"
            "</ul>\n"
            "Repeat for Phase 2 (Mid-scale) and Phase 3 (Steady State).\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "risk_management",
        "Institutional Risk Management",
        "RISK",
        "image-above",
        (
            "Create a professional Risk Management profile for {topic} projects.\n"
            "REQUIRED: Identify 4 high-stakes risks using specific industry terminology (e.g. 'clash detection errors', 'off-site tolerances').\n"
            "STRUCTURE — 4 risks, each with:\n"
            "<h3>[Technical Risk Name]</h3>\n"
            "<p><strong>Trigger:</strong> The specific event or condition in the {topic} workflow that causes the risk.</p>\n"
            "<p><strong>Mitigation Protocol:</strong> Detailed protocols or tools experts use to neutralize this risk.</p>\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "best_practices",
        "Professional Standards & Best Practices",
        "METHODS",
        "text-only",
        (
            "Outline professional Best Practices for {audience} in the {topic} domain.\n"
            "REQUIRED: Name at least 3 specific tools, platforms, or standards (e.g. Revit, LGSF panels, SIPs, PassiveHouse, ISO 19650).\n"
            "STRUCTURE — 4 practices, each with:\n"
            "<h3>[Practice Name]</h3>\n"
            "<p>The METHOD: Detailed implementation steps using [named tool/standard].</p>\n"
            "<p>The METRIC: The specific performance improvement (e.g. '22% reduction in RFI cycles').</p>\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "key_statistics",
        "Market Intelligence & Data Analysis",
        "DATA",
        "text-only",
        (
            "Provide critical market data and statistics relevant to {topic}.\n"
            "REQUIRED: Use credible-sounding (or real) data points attributed to 'Industry Benchmarks' or 'Market Research'.\n"
            "STRUCTURE:\n"
            "<h3>Global Industry Benchmarks</h3>\n"
            "<p>Provide 4-5 specific data points (e.g. 'Modular construction adoption in {industry} is projected to grow by 12.4% CAGR through 2028').</p>\n"
            "<h3>Comparative Operational Efficiency</h3>\n"
            "<ul>\n"
            "  <li><strong>Metric 1:</strong> Specific comparison (e.g. waste reduction vs traditional methods).</li>\n"
            "  <li><strong>Metric 2:</strong> Time-to-market reduction benchmarks.</li>\n"
            "  <li><strong>Metric 3:</strong> Cost-per-square-foot delta analysis.</li>\n"
            "</ul>\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "process_steps",
        "Technical Workflow Stages",
        "PROCESS",
        "text-only",
        (
            "Break down the technical process for implementing {topic}.\n"
            "REQUIRED: Use technical verbs and name specific workflow stages (e.g. 'Schematic Design', 'BIM Coordination', 'Factory Fabrication').\n"
            "STRUCTURE — 5 numbered steps using <h3>:\n"
            "<h3>Step 1: [Technical Stage Name]</h3>\n"
            "<p>Explain the inputs, tools used, and the specific output for {audience}.</p>\n"
            "Repeat for 5 steps.\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "comparison_table",
        "Strategic Comparative Analysis",
        "COMPARISON",
        "text-only",
        (
            "Provide a strategic comparative analysis between traditional methods and {topic}.\n"
            "REQUIRED: Use specific criteria (e.g. 'Embodied Carbon', 'Precision Tolerances', 'Site Disruption').\n"
            "STRUCTURE:\n"
            "<p>Intro sentence: Contextualize the shift from legacy to modern approaches.</p>\n"
            "<h3>[Criteria 1: Strategic Impact]</h3>\n"
            "<p>Contrast the two approaches with specific metrics and technical benefits.</p>\n"
            "<h3>[Criteria 2: Financial Performance]</h3>\n"
            "<p>Contrast with focus on {audience} pain points.</p>\n"
            "<h3>[Criteria 3: Lifecycle Value]</h3>\n"
            "<p>Analyze the long-term maintenance and performance delta.</p>\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "key_takeaways",
        "Strategic Takeaways & Pivots",
        "TAKEAWAYS",
        "text-only",
        (
            "Summarize the most important strategic insights for {audience}.\n"
            "REQUIRED: Focus on high-level strategic pivots. Name specific shifts in {topic}.\n"
            "STRUCTURE — 3 themes, each with <h3> + narrative <p> + <ul>:\n"
            "<h3>[Theme Name]</h3>\n"
            "<p>The core strategic insight in 3-4 sentences.</p>\n"
            "<ul>\n"
            "  <li>Specific actionable takeaway with a metric or tool reference.</li>\n"
            "</ul>\n"
            "Repeat for 3 themes.\n"
            "WORD COUNT: 350-400 words."
        )
    ),
    (
        "conclusion",
        "Conclusion & 90-Day Roadmap",
        "CONCLUSION",
        "text-only",
        (
            "Final conclusion and professional roadmap for adopting {topic}.\n"
            "REQUIRED: A strong, specific call to action tailored to {audience}.\n"
            "STRUCTURE:\n"
            "<p>Final summary of the strategic value and ROI of {topic}.</p>\n"
            "<h3>Your 90-Day Adoption Roadmap</h3>\n"
            "<ol>\n"
            "  <li><strong>Phase 1 (Day 1-30):</strong> Immediate technical audit and tool assessment.</li>\n"
            "  <li><strong>Phase 2 (Day 31-60):</strong> Workflow integration and pilot program.</li>\n"
            "  <li><strong>Phase 3 (Day 61-90):</strong> Metric verification and scaling.</li>\n"
            "</ol>\n"
            "WORD COUNT: 250-300 words."
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
        self.temperature = 0.4
        self.max_tokens  = 4096
        self._analysis   = None
        self._framework  = None

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
            
            sanitized = self._sanitize_html(
                content if isinstance(content, str) else str(content)
            )
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
        primary_color = firm_profile.get("primary_brand_color") or (signals or {}).get("primary_color") or "#1a365d"
        if primary_color and not str(primary_color).startswith("#"): primary_color = "#" + primary_color

        secondary_color = firm_profile.get("secondary_brand_color") or "#c5a059"
        if secondary_color and not str(secondary_color).startswith("#"): secondary_color = "#" + secondary_color

        accent_color = firm_profile.get("accent_color") or "#f8fafc"
        if accent_color and not str(accent_color).startswith("#"): accent_color = "#" + accent_color

        company_name = firm_profile.get("firm_name") or firm_profile.get("name") or (signals.get("topic") if signals else "Strategic Analysis")

        vars = {
            "documentTitle":     ai_content.get("title") or signals.get("topic") or "Guide",
            "primaryColor":      primary_color,
            "secondaryColor":    secondary_color,
            "accentColor":       accent_color,
            "documentTypeLabel": ai_content.get("document_type_label") or "STRATEGIC GUIDE",
            "mainTitle":         ai_content.get("title") or signals.get("topic") or "Strategic Guide",
            "documentSubtitle":  ai_content.get("subtitle") or f"A comprehensive look into {signals.get('topic', 'industry trends')}.",
            "companyName":       company_name,
            "emailAddress":      firm_profile.get("work_email", ""),
            "phoneNumber":       firm_profile.get("phone_number", ""),
            "website":           firm_profile.get("firm_website", ""),
            "logoPlaceholder":   company_name[:2].upper() if company_name else "AI",
            "differentiator":    firm_profile.get("branding_guidelines", "") or f"Leading experts in {signals.get('topic', 'the field')}.",
        }

        # Global variables for easy access in Template.html
        vars["vars"] = vars

        for idx, (key, title, label, _, _) in enumerate(SECTIONS):
            vars[f"sectionTitle{idx+1}"] = label
            vars[f"contentItem{idx+1}"] = title

        vars.update({
            "termsSummary":      ai_content.get("legal_notice_summary") or f"This report on {signals.get('topic', 'industry trends')} is provided for informational purposes only.",
            "termsParagraph1":   f"© {company_name}. All rights reserved.",
            "termsParagraph2":   f"The information contained in this document is for general guidance on {signals.get('topic', 'matters of interest')} only.",
            "termsParagraph3":   "Given the changing nature of laws and regulations, there may be delays, omissions or inaccuracies in information contained in this document.",
            "termsParagraph4":   "While we have made every attempt to ensure that the information in this document has been obtained from reliable sources, we are not responsible for any errors or omissions.",
            "termsParagraph5":   f"This AI-generated content is intended to support, not replace, professional advice in {signals.get('topic', 'the field')}.",
        })

        fw = ai_content.get("framework", {})
        for idx, (key, default_title, default_label, _, _) in enumerate(SECTIONS):
            section_fw = fw.get(key, {})
            title = section_fw.get("title") or default_title
            label = section_fw.get("kicker") or default_label
            s_idx = idx + 1
            content = ai_content.get(key, "")
            
            vars[f"customTitle{s_idx}"] = title
            vars[f"sectionTitle{idx+3}"] = label
            vars[f"customContent{s_idx}"] = self._extract_intro(content)
            
            sub_h = self._extract_subheadings(content)
            for h_idx, h_text in enumerate(sub_h):
                if h_idx < 1:
                    vars[f"subheading{s_idx}"] = h_text
                    vars[f"subcontent{s_idx}"] = self._extract_subcontent(content, h_text)

            boxes = self._extract_boxes(content)
            for b_idx, (b_title, b_content) in enumerate(boxes):
                if b_idx == 0: vars[f"boxContent{s_idx}"] = b_content

        # Add image URLs from firm_profile
        for i in range(1, 7):
            vars[f"image_{i}_url"] = firm_profile.get(f"image_{i}_url", "")

        vars.update({k: v for k, v in ai_content.items() if k not in ["title", "subtitle", "summary", "document_type", "document_type_label", "sections_config"]})

        vars.update({
            "ctaHeadline":       ai_content.get("cta_headline") or f"Next Steps for {vars['mainTitle']}",
            "ctaText":           ai_content.get("cta_text") or "Book a Consultation",
        })

        return vars

    def _extract_intro(self, html: str) -> str:
        match = re.search(r'<p>(.*?)</p>', html, re.S)
        return match.group(1).strip() if match else ""

    def _extract_subheadings(self, html: str) -> List[str]:
        return re.findall(r'<h3>(.*?)</h3>', html)

    def _extract_subcontent(self, html: str, subheading: str) -> str:
        pattern = rf'<h3>{re.escape(subheading)}</h3>\s*(.*?)(?:<h3>|$)'
        match = re.search(pattern, html, re.S)
        return match.group(1).strip() if match else ""

    def _extract_boxes(self, html: str) -> List[tuple]:
        matches = re.findall(r'<h3>(.*?)</h3>\s*(<p>.*?</p>|<ul>.*?</ul>)', html, re.S)
        return [(m[0], m[1]) for m in matches]

    def _extract_stats(self, html: str, data: Dict):
        vals = re.findall(r'<li><strong>(.*?)</strong>\s*:\s*(.*?)</li>', html)
        for i, (lbl, val) in enumerate(vals):
            if i < 3:
                data[f"stat{i+1}Value"] = val
                data[f"stat{i+1}Label"] = lbl

    def _extract_steps(self, html: str, data: Dict):
        steps = re.findall(r'<h3>Step \d+:\s*(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(steps):
            if i < 5:
                data[f"stepTitle{i+1}"] = ttl
                data[f"stepContent{i+1}"] = cnt

    def _extract_table(self, html: str, data: Dict):
        criteria = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(criteria):
            if i < 3: data[f"tableRow{i+1}Col1"] = ttl

    def _extract_icons(self, html: str, data: Dict):
        themes = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(themes):
            if i < 4:
                data[f"iconCard{i+1}Title"] = ttl
                data[f"iconCard{i+1}Text"] = cnt[:80] + "..." if len(cnt) > 80 else cnt

    def _extract_timeline(self, html: str, data: Dict):
        phases = re.findall(r'<h3>Phase \d+:\s*(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(phases):
            if i < 5:
                data[f"timelineItem{i+1}Title"] = ttl
                data[f"timelineItem{i+1}"] = cnt

    def _extract_checklists(self, html: str, data: Dict, prefix: str, limit: int):
        items = re.findall(r'<li>(.*?)</li>', html)
        for i, itm in enumerate(items):
            if i < limit: data[f"{prefix}{i+1}"] = itm

    def _extract_quote(self, html: str, data: Dict, idx: int):
        match = re.search(r'<blockquote>(.*?)</blockquote>', html, re.S)
        if match:
            data[f"quoteText{idx}"] = match.group(1).strip()
            data[f"quoteAuthor{idx}"] = "Industry Strategic Analysis"

    def _extract_cta(self, html: str, data: Dict):
        match = re.search(r'<h3>(.*?)</h3>', html)
        if match: data["ctaHeadline"] = match.group(1)

    def _analyze_inputs(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        system = "You are a strategic institutional industry analyst. Return valid JSON only. No markdown."
        prompt = (
            f"Analyze these inputs and return structured domain insights for an institutional-grade report.\n\n"
            f"Topic: {signals['topic']}\n"
            f"Audience: {signals['audience']}\n"
            f"Pain Points: {signals['pain_points']}\n\n"
            f"Return ONLY this JSON:\n"
            f'{{\n'
            f'  "industry_context": "Deep context on the current state of this industry",\n'
            f'  "core_problem_summary": "Root cause of why these pain points occur",\n'
            f'  "stakeholder_roles": ["role 1", "role 2"],\n'
            f'  "strategic_focus_areas": ["area 1", "area 2", "area 3"],\n'
            f'  "risk_factors": ["risk 1", "risk 2"],\n'
            f'  "pain_point_solutions": {{ "pain point": "framework name" }},\n'
            f'  "implementation_priorities": ["priority 1", "priority 2"]\n'
            f'}}'
        )
        return self._call_ai(system, prompt, max_tokens=500)

    def _generate_framework(self, analysis: Dict[str, Any], section_keys: List[str], signals: Dict[str, Any]) -> Dict[str, Any]:
        system = "You are a senior institutional content strategist. Return valid JSON only. No markdown."
        keys_str = json.dumps(section_keys)
        prompt = (
            f"Define a writing plan for an institutional-grade guide.\n"
            f"Topic: {signals['topic']} | Audience: {signals['audience']}\n"
            f"DOMAIN INSIGHTS: {json.dumps(analysis)}\n\n"
            f"For EACH key in {keys_str}, return:\n"
            f"  title: 3-5 word domain-specific heading\n"
            f"  kicker: 1-word uppercase label\n"
            f"  angle: 1-sentence editorial angle\n"
            f"  key_points: exactly 3 specific points\n"
            f"  pain_point_tie: which pain point it resolves\n\n"
            f"Return ONLY: {{\"sections\": {{ \"key\": {{...}} }} }}"
        )
        result = self._call_ai(system, prompt, max_tokens=1500)
        if "sections" not in result and isinstance(result, dict): result = {"sections": result}
        return result

    def _generate_title(self, signals: Dict, type_label: str) -> Dict:
        system = "You are a senior document strategist. Return valid JSON only. No markdown."
        prompt = (
            f"Generate institutional metadata for a {type_label} on: {signals['topic']}\n"
            f"Return ONLY: {{\"title\":\"...\",\"subtitle\":\"...\",\"target_audience_summary\":\"...\",\"legal_notice_summary\":\"...\",\"cta_headline\":\"...\",\"cta_text\":\"...\"}}"
        )
        return self._call_ai(system, prompt, max_tokens=400)

    def _generate_section(self, key: str, title: str, brief: str, signals: Dict) -> str:
        brief_filled = brief.format(topic=signals["topic"], audience=signals["audience"], pain_points=signals["pain_points"], industry=signals.get("industry") or signals["topic"])
        analysis = self._analysis
        secs     = self._framework.get("sections", {})
        sec_plan = secs.get(key, {})
        
        system = (
            f"You are a domain expert and senior consultant in {signals['topic']}.\n"
            f"Write one section of an institutional-grade professional guide.\n\n"
            f"INDUSTRY CONTEXT: {analysis.get('industry_context', '')}\n"
            f"CORE PROBLEM: {analysis.get('core_problem_summary', '')}\n"
            f"ANGLE: {sec_plan.get('angle', '')}\n\n"
            f"RULES:\n"
            f"1. Authority: Institutional, authoritative, precise.\n"
            f"2. HTML: <p> <strong> <em> <h3> <h4> <ul> <ol> <li> <br> only.\n"
            f"3. NO TITLES in content.\n"
            f"4. MINIMUM WORD COUNT: 350-400 words. Expand with technical details, workflow metrics, and deep analysis.\n"
            f"5. Return valid JSON: {{\"key\": \"HTML\"}} only.\n"
        )
        prompt = f"Write the '{title}' section.\nBRIEF: {brief_filled}\nReturn ONLY: {{\"{key}\": \"HTML\"}}"
        raw = self._call_ai(system, prompt, max_tokens=1800)
        return self._sanitize_html(self._extract_content(raw, key))

    def _extract_content(self, result: Dict, key: str) -> str:
        if not result: return ""
        if key in result and isinstance(result[key], str): return result[key]
        for k, v in result.items():
            if isinstance(v, str) and len(v) > 100: return v
        return ""

    def _sanitize_html(self, html: str) -> str:
        if not html: return html
        html = html.strip().strip('"')
        html = re.sub(r'<(/?)(\w+)([^>]*)>', lambda m: m.group(0) if m.group(2).lower() in ALLOWED_TAGS else "", html)
        return self._ensure_closed_tags(html).strip()

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            raise RuntimeError(f"Groq API failed: {e}")

    def _ensure_closed_tags(self, html: str) -> str:
        void = {"br", "hr", "img", "input", "link", "meta"}
        tags = re.findall(r"<(/?)([a-zA-Z1-6]+)", html)
        stack = []
        for closing, tag in tags:
            tag = tag.lower()
            if tag in void: continue
            if closing:
                if stack and stack[-1] == tag: stack.pop()
            else: stack.append(tag)
        for tag in reversed(stack): html += f"</{tag}>"
        return html

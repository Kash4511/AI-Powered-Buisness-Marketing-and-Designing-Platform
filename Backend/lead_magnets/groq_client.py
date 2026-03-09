import os
import json
import logging
import time
import re
from typing import Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)

SECTIONS = [
    (
        "executive_summary",
        "Executive Summary",
        "OVERVIEW",
        "text-only",
        (
            "Write the Executive Summary for a professional guide on {topic} for {audience}.\n"
            "REQUIRED: Use at least 2 specific industry metrics with context (e.g. 'average lifecycle cost reduction of 18% in LGSF projects').\n"
            "STRUCTURE:\n"
            "<p> — 2-3 sentences: what {topic} means operationally for {audience}.\n"
            "<p> — 2-3 sentences: current industry shifts in {topic}.\n"
            "<h3>Strategic Drivers</h3>\n"
            "<ul> — exactly one <li> per pain point in [{pain_points}]. Use <strong> for the pain point.\n"
            "<p> — final outcome statement.\n"
            "BANNED: vague percentages like '25% increase' without a source or baseline."
        )
    ),
    (
        "key_challenges",
        "Key Challenges",
        "CHALLENGES",
        "image-right",
        (
            "Write the Key Challenges for {audience} in {topic}.\n"
            "REQUIRED: Name specific failure modes (e.g. 'BIM data siloed in Revit 2024') and technical blockers.\n"
            "STRUCTURE — for EACH pain point in [{pain_points}]:\n"
            "<h3>[Pain point name]</h3>\n"
            "<p><strong>Technical Root Cause:</strong> 1-2 sentences on the mechanical/software reason this fails.</p>\n"
            "<p><strong>Operational Impact:</strong> 1-2 sentences with a specific metric (e.g. 'man-hour loss', 'waste percentage').</p>\n"
            "<p><strong>Real-World Scenario:</strong> A realistic {topic} situation involving specific tools or roles.\n"
            "BANNED: generic advice, 'leverage', 'unlock'."
        )
    ),
    (
        "strategic_framework",
        "Strategic Framework",
        "FRAMEWORK",
        "image-left",
        (
            "Define a Strategic Framework for {topic} for {audience}.\n"
            "REQUIRED: Name a specific proprietary-sounding framework (e.g. 'The Modular Synthesis Protocol').\n"
            "STRUCTURE:\n"
            "<p> — Intro to the framework logic.\n"
            "<h3>[Step 1: Domain-Specific Name]</h3>\n"
            "<p> — What practitioners DO. Name specific software (e.g. Procore, Autodesk Construction Cloud) or hardware.\n"
            "<h3>[Step 2: Technical Integration]</h3>\n"
            "<p> — How it resolves one of [{pain_points}]. Use a real-world metric.\n"
            "<h3>[Step 3: Optimization]</h3>\n"
            "<p> — Advanced workflow step (e.g. 'DFMA analysis', 'carbon sequestration metrics').\n"
            "Total 200-240 words."
        )
    ),
    (
        "implementation_strategy",
        "Implementation Strategy",
        "IMPLEMENTATION",
        "text-only",
        (
            "Write a detailed Implementation Strategy for {topic}.\n"
            "REQUIRED: This must be a narrative roadmap, NOT just a list of tasks. Connect tasks to outcomes.\n"
            "STRUCTURE — 3 Phases, each with <h3> + narrative <p> + <ul>:\n"
            "<h3>Phase 1: [Technical Kickoff Name]</h3>\n"
            "<p>Explain the goal of this phase in 3 sentences, referencing specific {topic} standards.</p>\n"
            "<ul>\n"
            "  <li><strong>Milestone:</strong> specific technical achievement.</li>\n"
            "  <li><strong>Risk Factor:</strong> how to avoid a [{pain_points}] failure here.</li>\n"
            "</ul>\n"
            "Repeat for Phase 2 (Mid-scale) and Phase 3 (Steady State).\n"
            "BANNED: skeletal bullet points without context."
        )
    ),
    (
        "risk_management",
        "Risk Management",
        "RISK",
        "image-above",
        (
            "Write a Risk Management profile for {topic}.\n"
            "REQUIRED: Identify 4 high-stakes risks. Use specific industry terminology (e.g. 'clash detection errors', 'off-site tolerances').\n"
            "STRUCTURE — 4 risks, each with:\n"
            "<h3>[Technical Risk Name]</h3>\n"
            "<p><strong>Trigger:</strong> specific event in {topic} workflow.</p>\n"
            "<p><strong>Mitigation:</strong> exactly how expert {audience} use tools or protocols to fix it.\n"
            "BANNED: 'scope creep', 'budget overrun'."
        )
    ),
    (
        "best_practices",
        "Best Practices",
        "METHODS",
        "text-only",
        (
            "Write Best Practices for {audience} in {topic}.\n"
            "REQUIRED: Name at least 2 specific tools, platforms, or standards (e.g. Revit, LGSF panels, SIPs, PassiveHouse, ISO 19650).\n"
            "STRUCTURE — 4 practices, each with:\n"
            "<h3>[Practice Name]</h3>\n"
            "<p>The METHOD: how to implement this specifically using [named tool/standard].</p>\n"
            "<p>The METRIC: specific improvement (e.g. '22% reduction in RFI cycles').</p>\n"
            "BANNED: vague advice like 'Plan Ahead'."
        )
    ),
    (
        "key_statistics",
        "Key Statistics & Market Data",
        "DATA",
        "text-only",
        (
            "Provide critical market data and statistics for {topic}.\n"
            "REQUIRED: Use credible-sounding (or real) data points. Attribute them to 'Industry Benchmarks', 'Market Research', or 'Historical Project Data'.\n"
            "STRUCTURE:\n"
            "<h3>Industry Benchmarks</h3>\n"
            "<p>Provide 3-4 specific data points (e.g. 'Modular construction adoption in {industry} is projected to grow by 12.4% CAGR through 2028').</p>\n"
            "<h3>Comparative Efficiency</h3>\n"
            "<ul>\n"
            "  <li>Metric 1: Specific comparison (e.g. 'Off-site vs On-site waste reduction').</li>\n"
            "  <li>Metric 2: Time-to-market reduction.</li>\n"
            "</ul>\n"
            "BANNED: fabricated percentages without a clear baseline."
        )
    ),
    (
        "process_steps",
        "Technical Process Steps",
        "PROCESS",
        "text-only",
        (
            "Break down the technical process for {topic}.\n"
            "REQUIRED: Use technical verbs and name specific workflow stages (e.g. 'Schematic Design', 'BIM Coordination', 'Factory Fabrication').\n"
            "STRUCTURE — 5 numbered steps using <h3>:\n"
            "<h3>Step 1: [Technical Stage Name]</h3>\n"
            "<p>Explain the inputs, tools used, and the specific output for {audience}.</p>\n"
            "Repeat for 5 steps."
        )
    ),
    (
        "comparison_table",
        "Strategic Comparison",
        "COMPARISON",
        "text-only",
        (
            "Write a comparative analysis between traditional methods and {topic}.\n"
            "REQUIRED: Use specific criteria (e.g. 'Embodied Carbon', 'Precision Tolerances', 'Site Disruption').\n"
            "STRUCTURE:\n"
            "<p>Intro sentence.</p>\n"
            "<h3>[Criteria 1]</h3>\n"
            "<p>Contrast the two approaches with specific metrics.</p>\n"
            "<h3>[Criteria 2]</h3>\n"
            "<p>Contrast with focus on {audience} pain points.</p>\n"
            "Repeat for 3 criteria."
        )
    ),
    (
        "key_takeaways",
        "Key Takeaways",
        "TAKEAWAYS",
        "text-only",
        (
            "Summarize the most important insights for {audience}.\n"
            "REQUIRED: Focus on high-level strategic pivots. Name specific shifts in {topic}.\n"
            "STRUCTURE — 3 themes, each with <h3> + narrative <p> + <ul>:\n"
            "<h3>[Theme Name]</h3>\n"
            "<p>The core strategic insight.</p>\n"
            "<ul>\n"
            "  <li>Specific takeaway with a metric or tool reference.</li>\n"
            "</ul>\n"
            "Repeat for 3 themes."
        )
    ),
    (
        "conclusion",
        "Conclusion & Roadmap",
        "CONCLUSION",
        "text-only",
        (
            "Final conclusion and next steps for {topic}.\n"
            "REQUIRED: A strong, specific call to action tailored to {audience}.\n"
            "STRUCTURE:\n"
            "<p>Final summary of the value of {topic}.</p>\n"
            "<h3>Your 90-Day Roadmap</h3>\n"
            "<ol>\n"
            "  <li>Immediate action: specific {topic} audit.</li>\n"
            "  <li>Tool implementation: name a specific software/method.</li>\n"
            "  <li>Metric verification.</li>\n"
            "</ol>\n"
            "Total 180-220 words."
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

# Section key → layout type mapping (used by map_to_template_vars)
SECTION_LAYOUT = {key: layout for key, _, _, layout, _ in SECTIONS}


class GroqClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")
        self.client      = Groq(api_key=api_key)
        self.model       = "llama-3.3-70b-versatile"   # swap to llama-3.3-70b-versatile for production
        self.temperature = 0.45
        self.max_tokens  = 4096
        self._analysis   = None   # Layer 1 cache
        self._framework  = None   # Layer 2 cache

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
        type_label = DOC_TYPE_LABELS.get(doc_type) or DOC_TYPE_LABELS["guide"]
        logger.info(f"📄 {type_label} | topic={signals['topic']} | model={self.model}")

        # ── Layer 1: Understand the topic/audience deeply (~400 tokens, 1 call)
        logger.info("🧠 Layer 1 — Input Analysis")
        self._analysis = self._analyze_inputs(signals)

        # ── Layer 2: Build per-section writing blueprint (~800 tokens, 1 call)
        logger.info("📐 Layer 2 — Framework Generation")
        section_keys = [key for key, _, _, _, _ in SECTIONS]
        self._framework = self._generate_framework(self._analysis, section_keys, signals)

        # ── Layer 3: Title + 8 sections, each with full context (~1800 tokens × 9)
        title_data = self._generate_title(signals, type_label)
        expansions: Dict[str, str] = {}
        for key, title, label, _layout, brief in SECTIONS:
            logger.info(f"✍️  Layer 3 — {key}")
            expansions[key] = self._generate_section(key, title, brief, signals)

        # Clear cache
        self._analysis  = None
        self._framework = None

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
            "title":               raw.get("title") or "",
            "subtitle":            raw.get("subtitle", ""),
            "summary":             raw.get("target_audience_summary", ""),
            "document_type":       raw.get("document_type", "guide"),
            "document_type_label": raw.get("document_type_label") or "",
            "sections_config":     SECTIONS,
        }
        for key, *_ in SECTIONS:  # key, title, label, layout, brief
            content = exp.get(key, "")
            if isinstance(content, dict):
                content = json.dumps(content)
            
            sanitized = self._sanitize_html(
                content if isinstance(content, str) else str(content)
            )
            normalized[key] = sanitized
            
            # Extract specific components for the new magazine layout
            if key == "key_statistics":
                self._extract_stats(sanitized, normalized)
                self._extract_strip(sanitized, normalized, 1)
            elif key == "process_steps":
                self._extract_steps(sanitized, normalized)
            elif key == "comparison_table":
                self._extract_table(sanitized, normalized)
                self._extract_quote(sanitized, normalized, 3)
            elif key == "key_takeaways":
                self._extract_icons(sanitized, normalized)
            elif key == "implementation_strategy":
                self._extract_timeline(sanitized, normalized)
            elif key == "best_practices":
                self._extract_checklists(sanitized, normalized, "extListItem", 6)
                self._extract_strip(sanitized, normalized, 2)
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
        primary_color = (
            firm_profile.get("primary_brand_color")
            or (signals or {}).get("primary_color") or "#1a1a1a"
        )
        if primary_color and not str(primary_color).startswith("#"):
            primary_color = "#" + primary_color

        secondary_color = firm_profile.get("secondary_brand_color") or "#2a2a2a"
        if secondary_color and not str(secondary_color).startswith("#"):
            secondary_color = "#" + secondary_color

        accent_color = firm_profile.get("accent_color") or "#3a3a3a"
        if accent_color and not str(accent_color).startswith("#"):
            accent_color = "#" + accent_color

        highlight_color = firm_profile.get("highlight_color") or "#4a4a4a"
        if highlight_color and not str(highlight_color).startswith("#"):
            highlight_color = "#" + highlight_color

        gold_color = firm_profile.get("gold_color") or "#c5a059"
        if gold_color and not str(gold_color).startswith("#"):
            gold_color = "#" + gold_color

        company_name = (
            firm_profile.get("firm_name")
            or firm_profile.get("company_name")
            or "Your Company"
        )

        # Base mapping
        vars = {
            "documentTitle":     ai_content.get("title"),
            "primaryColor":      primary_color,
            "secondaryColor":    secondary_color,
            "accentColor":       accent_color,
            "highlightColor":    highlight_color,
            "goldColor":         gold_color,
            "documentTypeLabel": ai_content.get("document_type_label"),
            "mainTitle":         ai_content.get("title"),
            "mainTitleAccent":   "", # AI usually generates this in subtitle or we can split title
            "documentSubtitle":  ai_content.get("subtitle"),
            "companyName":       company_name,
            "emailAddress":      firm_profile.get("work_email", ""),
            "phoneNumber":       firm_profile.get("phone_number", ""),
            "website":           firm_profile.get("firm_website", ""),
            "logoPlaceholder":   company_name[0].upper(),
            "footerText":        f"© {company_name}",
        }

        # Split title for accent if possible
        title = vars["mainTitle"]
        if ":" in title:
            parts = title.split(":", 1)
            vars["mainTitle"] = parts[0].strip()
            vars["mainTitleAccent"] = parts[1].strip()

        # Section Titles and Page Numbers
        for idx, (key, title, label, _, _) in enumerate(SECTIONS):
            vars[f"sectionTitle{idx+1}"] = label
            vars[f"pageNumberHeader{idx+1}"] = f"{idx+2:02d}" # Starting from page 2 (Terms)
            vars[f"contentItem{idx+1}"] = title
            vars[f"pageNumber{idx+4}"] = f"{idx+4:02d}" # Starting from page 4 (Content)

        # Terms Page (Page 2)
        vars.update({
            "sectionTitle1": "LEGAL NOTICE",
            "pageNumberHeader2": "02",
            "termsTitle": "Terms of Use",
            "termsSummary": "This report is provided for informational purposes only. The contents are based on AI-assisted analysis and should be verified by professional consultants before implementation.",
            "termsParagraph1": f"© {company_name}. All rights reserved. No part of this publication may be reproduced, distributed, or transmitted in any form or by any means, including photocopying, recording, or other electronic or mechanical methods, without the prior written permission of the publisher.",
            "termsParagraph2": "The information contained in this document is for general guidance on matters of interest only. The application and impact of laws can vary widely based on the specific facts involved.",
            "termsParagraph3": "Given the changing nature of laws, rules and regulations, and the inherent hazards of electronic communication, there may be delays, omissions or inaccuracies in information contained in this document.",
            "termsParagraph4": "While we have made every attempt to ensure that the information contained in this document has been obtained from reliable sources, we are not responsible for any errors or omissions, or for the results obtained from the use of this information.",
            "termsParagraph5": "This AI-generated content is intended to support, not replace, professional architectural and engineering advice. Consult with qualified professionals for project-specific requirements.",
        })

        # TOC Page (Page 3)
        vars.update({
            "sectionTitle2": "CONTENTS",
            "pageNumberHeader3": "03",
            "contentsTitle": "Table of Contents",
        })

        # Content Sections (Pages 4-13)
        for idx, (key, title, label, _, _) in enumerate(SECTIONS):
            s_idx = idx + 1
            content = ai_content.get(key, "")
            
            vars[f"customTitle{s_idx}"] = title
            vars[f"customContent{s_idx}"] = self._extract_intro(content)
            
            # Subheadings and Subcontent
            sub_h = self._extract_subheadings(content)
            for h_idx, h_text in enumerate(sub_h):
                if h_idx < 1: # Usually one main subheading per page in this layout
                    vars[f"subheading{s_idx}"] = h_text
                    vars[f"subcontent{s_idx}"] = self._extract_subcontent(content, h_text)

            # Box Content (Callouts)
            boxes = self._extract_boxes(content)
            for b_idx, (b_title, b_content) in enumerate(boxes):
                v_idx = b_idx + 1
                if v_idx <= 4:
                    vars[f"boxTitle{v_idx}"] = b_title
                    vars[f"boxContent{v_idx}"] = b_content
                # Also map to accentBox for specific pages
                if s_idx == 5: vars[f"accentBoxTitle3"] = b_title; vars[f"accentBoxContent3"] = b_content
                if s_idx == 8: vars[f"accentBoxTitle4"] = b_title; vars[f"accentBoxContent4"] = b_content

        # Include extracted specialized components (Stats, Steps, Table, Icons, Timeline)
        # These were added to the ai_content dict by normalize_ai_output
        vars.update({k: v for k, v in ai_content.items() if k not in ["title", "subtitle", "summary", "document_type", "document_type_label", "sections_config"]})

        # Images
        vars.update({
            "image1Html": self._get_image_html(firm_profile.get("image_1_url")),
            "image2Html": self._get_image_html(firm_profile.get("image_2_url")),
            "image3Html": self._get_image_html(firm_profile.get("image_3_url")),
            "architecturalImageCaption1": firm_profile.get("image_1_caption") or "Executive Summary Overview",
            "architecturalImageCaption2": firm_profile.get("image_2_caption") or "Key Challenges Analysis",
            "architecturalImageCaption3": firm_profile.get("image_3_caption") or "Strategic Framework Model",
        })

        # CTA Page (Page 14)
        vars.update({
            "sectionTitle8": "CONTACT",
            "pageNumberHeader9": f"{len(SECTIONS)+3:02d}",
            "ctaHeadline": ai_content.get("cta_headline") or f"Ready to Master {vars['mainTitle']}?",
            "contactDescription": ai_content.get("contact_description") or "Let's discuss how we can apply these strategies to your specific business challenges.",
            "whyChooseUsTitle": "Why Choose Us",
            "differentiator": ai_content.get("differentiator") or f"We combine industry expertise with cutting-edge {vars['mainTitle']} methodologies to deliver measurable results.",
            "ctaText": ai_content.get("cta_text") or "Book a Strategic Audit",
            "differentiatorTitle": ai_content.get("differentiator_title") or "Expert Guidance for Modern Construction",
        })

        return vars

    # ── EXTRACTION HELPERS ───────────────────────────────────────────────────

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
        # Look for <h3> followed by <p> or <ul> as potential box content
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
        data["tableHeader1"] = "Criteria"
        data["tableHeader2"] = "Traditional"
        data["tableHeader3"] = "Modular"
        data["tableHeader4"] = "Impact"
        for i, (ttl, cnt) in enumerate(criteria):
            if i < 3:
                data[f"tableRow{i+1}Col1"] = ttl
                # Split content if it has vs or contrast
                parts = re.split(r' vs | contrast | compared to ', cnt, flags=re.I)
                data[f"tableRow{i+1}Col2"] = parts[0] if len(parts) > 0 else "Standard"
                data[f"tableRow{i+1}Col3"] = parts[1] if len(parts) > 1 else "Optimized"
                data[f"tableRow{i+1}Col4"] = "High"

    def _extract_icons(self, html: str, data: Dict):
        themes = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        emojis = ["🚀", "🎯", "🛡️", "📈"]
        for i, (ttl, cnt) in enumerate(themes):
            if i < 4:
                data[f"iconCard{i+1}Emoji"] = emojis[i]
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
            if i < limit:
                data[f"{prefix}{i+1}"] = itm

    def _extract_quote(self, html: str, data: Dict, idx: int):
        match = re.search(r'<blockquote>(.*?)</blockquote>', html, re.S)
        if match:
            data[f"quoteText{idx}"] = match.group(1).strip()
            data[f"quoteAuthor{idx}"] = "Industry Insight"

    def _extract_strip(self, html: str, data: Dict, idx: int):
        # Extract <h3> followed by <p> as a highlight strip
        match = re.search(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        if match:
            data[f"highlightStripTitle{idx}"] = match.group(1)
            data[f"highlightStripContent{idx}"] = match.group(2)

    def _extract_cta(self, html: str, data: Dict):
        match = re.search(r'<h3>(.*?)</h3>', html)
        if match: data["ctaHeadline"] = match.group(1)
        
        intro = self._extract_intro(html)
        if intro: data["contactDescription"] = intro

    def _get_image_html(self, url: str) -> str:
        if url:
            return f'<img src="{url}" alt="Project Image">'
        return '<div class="img-ph"><span class="img-ph-icon">🖼️</span><span class="img-ph-label">Project Image</span></div>'

    def ensure_section_content(self, sections, signals, firm_profile):
        return sections

    # ── PRIVATE ───────────────────────────────────────────────────────────────

    def _analyze_inputs(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 1 — extract deep domain insights from user inputs."""
        system = "You are a strategic industry analyst. Return valid JSON only. No markdown."
        prompt = (
            f"Analyze these inputs and return structured domain insights.\n\n"
            f"Topic: {signals['topic']}\n"
            f"Audience: {signals['audience']}\n"
            f"Pain Points: {signals['pain_points']}\n\n"
            f"Return ONLY this JSON:\n"
            f'{{\n'
            f'  "industry_context": "2-sentence description of the current state of this industry",\n'
            f'  "core_problem_summary": "1-sentence root cause of why these pain points occur in {signals["topic"]}",\n'
            f'  "stakeholder_roles": ["role specific to this topic", "another role"],\n'
            f'  "strategic_focus_areas": ["domain-specific area 1", "area 2", "area 3"],\n'
            f'  "risk_factors": ["specific risk in {signals["topic"]}", "another risk"],\n'
            f'  "pain_point_solutions": {{\n'
            f'    "exact pain point text": "specific solution framework name for this topic"\n'
            f'  }},\n'
            f'  "implementation_priorities": ["priority 1 specific to topic", "priority 2"]\n'
            f'}}'
        )
        logger.info(f"🔵 Layer 1 | {signals['topic']}")
        result = self._call_ai(system, prompt, max_tokens=500)
        logger.info(f"✅ Layer 1 done | keys={list(result.keys())}")
        return result

    def _generate_framework(self, analysis: Dict[str, Any], section_keys: List[str], signals: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 2 — build per-section editorial blueprint using exact section keys."""
        system = "You are a senior content strategist. Return valid JSON only. No markdown."
        # Give Groq the exact key names it must use — prevents title vs key mismatch
        keys_str = json.dumps(section_keys)
        prompt = (
            f"You are planning a professional guide.\n"
            f"Topic: {signals['topic']} | Audience: {signals['audience']}\n"
            f"Pain Points: {signals['pain_points']}\n\n"
            f"DOMAIN INSIGHTS:\n{json.dumps(analysis, indent=2)}\n\n"
            f"For EACH of these section keys, define a writing plan:\n{keys_str}\n\n"
            f"For every key return:\n"
            f"  angle: 1-sentence editorial angle specific to this topic + audience\n"
            f"  key_points: exactly 3 specific points the writer MUST cover (domain-specific, not generic)\n"
            f"  pain_point_tie: which pain point from [{signals['pain_points']}] this section resolves\n\n"
            f"Return ONLY a JSON object where the 'sections' key contains all requested section keys.\n"
            f"Example structure:\n"
            f'{{"sections": {{ "executive_summary": {{"angle": "...", "key_points": [], "pain_point_tie": "..."}} }} }}'
        )
        logger.info(f"🔵 Layer 2 | {len(section_keys)} sections")
        result = self._call_ai(system, prompt, max_tokens=1500)
        # Normalise: if Groq returned keys directly (no "sections" wrapper), wrap them
        if "sections" not in result and isinstance(result, dict):
            if any(k in result for k in section_keys):
                result = {"sections": result}
                logger.warning("⚠️ Layer 2 — wrapped bare dict in 'sections'")
        logger.info(f"✅ Layer 2 done | section_keys={list(result.get('sections', {}).keys())}")
        return result

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
        """Layer 3 — write one section with full Layer 1+2 context injected."""
        brief_filled = brief.format(
            topic       = signals["topic"],
            audience    = signals["audience"],
            pain_points = signals["pain_points"],
            industry    = signals.get("industry") or signals["topic"],
        )

        # Pull Layer 1 + Layer 2 context for this section
        if not self._analysis or not self._framework:
            raise RuntimeError("Layer 1/2 context missing — _analyze_inputs and _generate_framework must run before _generate_section")
        analysis = self._analysis
        secs     = self._framework.get("sections", {})
        sec_plan = secs.get(key)
        if not isinstance(sec_plan, dict):
            raise RuntimeError(f"Layer 2 framework missing plan for section '{key}'. Got keys: {list(secs.keys())}")

        pain_tie  = sec_plan.get("pain_point_tie", "")
        solution  = analysis.get("pain_point_solutions", {}).get(pain_tie, "")
        angle     = sec_plan.get("angle", "")
        key_pts   = sec_plan.get("key_points", [])

        system = (
            f"You are a domain expert and senior consultant in {signals['topic']}.\n"
            f"You are writing one section of a professional lead-magnet guide.\n\n"
            # Layer 1 context
            f"INDUSTRY CONTEXT: {analysis.get('industry_context', '')}\n"
            f"CORE PROBLEM: {analysis.get('core_problem_summary', '')}\n\n"
            # Layer 2 context
            f"THIS SECTION'S ANGLE: {angle}\n"
            f"PAIN POINT THIS RESOLVES: {pain_tie}\n"
            f"SOLUTION FRAMEWORK: {solution}\n\n"
            f"NON-NEGOTIABLE RULES:\n"
            f"1. Every sentence must be specific to '{signals['topic']}' — no generic advice.\n"
            f"2. Directly address: {signals['pain_points']}\n"
            f"3. Write for: {signals['audience']}\n"
            f"4. BANNED: 'leverage', 'synergies', 'optimize solutions', 'unlock value', "
            f"'drive innovation', 'holistic approach', 'best-in-class'\n"
            f"5. HTML ONLY: <p> <strong> <em> <h3> <h4> <ul> <ol> <li> <br>. NEVER <div> <span> <table> <img>.\n"
            f"6. DO NOT write the section title — it renders above your content automatically.\n"
            f"7. STRUCTURE RULE: follow the SECTION BRIEF structure exactly — use the HTML elements specified.\n"
            f"8. CONTENT DENSITY: prefer 3-5 shorter paragraphs over 1-2 long ones. Break at every logical point.\n"
            f"9. MINIMUM WORD COUNT: Every section MUST be at least 180-220 words. If you are naturally concise, expand with specific technical details, real-world analogies, or workflow metrics.\n"
            f"10. Return valid JSON only. No markdown. No text outside the JSON.\n"
        )

        prompt = (
            f"Write the '{title}' section for a {signals['topic']} guide.\n\n"
            + (f"KEY POINTS TO COVER (mandatory — weave all 3 in):\n" + "\n".join(f"- {p}" for p in key_pts) + "\n\n" if key_pts else "")
            + f"SECTION BRIEF:\n{brief_filled}\n\n"
            f"SPECIAL REQUESTS: {signals.get('special') or 'None'}\n\n"
            f'Return ONLY: {{"{key}": "your full HTML content here"}}'
        )

        logger.info(f"🔵 Layer 3 — '{key}'")
        raw     = self._call_ai(system, prompt, max_tokens=1800)
        content = self._extract_content(raw, key)
        words   = len(content.split()) if content else 0
        logger.info(f"✅ '{key}': {words} words | angle='{angle[:40]}...' " if angle else f"✅ '{key}': {words} words")

        # Thresholds: conclusion can be shorter (80), others need 100+
        min_words = 80 if key == "conclusion" else 100
        if words < min_words:
            raise ValueError(f"Section '{key}' too short ({words} words — need {min_words}+). Keys: {list(raw.keys())}. Snippet: {str(raw)[:200]}")

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
        html = html.strip()
        if html.startswith('"') and html.endswith('"'):
            html = html[1:-1].strip()
        html = re.sub(r'\[IMAGE_PLACEHOLDER:[^\]]*\]', '', html)
        html = re.sub(
            r'<(/?)(\w+)([^>]*)>',
            lambda m: m.group(0) if m.group(2).lower() in ALLOWED_TAGS else "",
            html
        )
        html = re.sub(r'(?:^)"(?=<)', '', html)
        html = re.sub(r'(?<=>)"(?:$)', '', html)
        return self._ensure_closed_tags(html).strip()

    def _contrast_color(self, hex_color: str) -> str:
        """Return #fff or #000 depending on which is more legible on hex_color."""
        try:
            h = hex_color.lstrip("#")
            if len(h) == 3:
                h = "".join(c*2 for c in h)
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if brightness > 128 else "#ffffff"
        except Exception:
            return "#ffffff"

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
            )
        except Exception as e:
            logger.error(f"❌ Groq API: {type(e).__name__}: {e}\n{_tb.format_exc()}")
            raise RuntimeError(f"Groq API failed: {type(e).__name__}: {e}") from e

        finish   = response.choices[0].finish_reason
        raw_text = response.choices[0].message.content
        logger.info(f"🟢 finish={finish} | chars={len(raw_text)}")

        if finish == "length":
            raise ValueError(f"Groq truncated (finish=length, max_tokens={tokens}). Raw: {raw_text[:200]}")
        if not raw_text.strip():
            raise ValueError(f"Groq empty response. finish={finish}")

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

        # Repair: Groq returned {"key": <unquoted html>}
        m_repair = re.search(r'\{"(\w+)"\s*:\s*([^"\{][\s\S]*?)\s*\}\s*$', cleaned)
        if m_repair:
            try:
                parsed = json.loads(json.dumps({m_repair.group(1): m_repair.group(2).strip()}))
                logger.warning(f"⚠️ repaired unquoted value | keys={list(parsed.keys())}")
                return parsed
            except Exception:
                pass

        # Last-resort extraction: grab content after the first key's colon
        m_key = re.search(r'"(\w+)"\s*:\s*', cleaned)
        if m_key:
            key_name    = m_key.group(1)
            content_val = cleaned[m_key.end():].rstrip().rstrip("}")
            if content_val.strip():
                logger.warning(f"⚠️ raw extraction for key='{key_name}'")
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
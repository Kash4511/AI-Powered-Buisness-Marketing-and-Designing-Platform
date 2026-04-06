import os
import re
import logging
import time
from typing import Dict, Any, List, Tuple, Optional
from groq import Groq
import openai
import anthropic
import google.generativeai as genai

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# AI CONFIGURATIONS — Comparative settings for fallback models
# ─────────────────────────────────────────────────────────────────────────────
AI_CONFIGS = {
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 4096,
        "description": "High-speed Llama-3 (Groq)",
        "context_window": 128000,
    },
    "groq_fallback": {
        "model": "llama-3.1-8b-instant",
        "max_tokens": 4096,
        "description": "Llama-3 8B (Groq Fallback)",
        "context_window": 128000,
    },
    "anthropic": {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 8192,
        "description": "Premium reasoning & depth (Anthropic)",
        "context_window": 200000,
    },
    "openai": {
        "model": "gpt-4o-2024-08-06",
        "max_tokens": 4096,
        "description": "Industry-standard precision (OpenAI)",
        "context_window": 128000,
    },
    "google": {
        "model": "gemini-1.5-pro",
        "max_tokens": 8192,
        "description": "Massive context & detail (Google)",
        "context_window": 2000000,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# SECTION DEFINITIONS — Type-specific structures
# ─────────────────────────────────────────────────────────────────────────────

GUIDE_SECTIONS = [
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

CHECKLIST_SECTIONS = [
    ("introduction",           "Introduction",              "OVERVIEW",   "text-only", ""),
    ("pre_requisites",         "Pre-Implementation",        "PRE-REQS",   "text-only", ""),
    ("critical_milestones",    "Critical Milestones",       "MILESTONES", "text-only", ""),
    ("step_by_step_process",   "Step-by-Step Execution",    "EXECUTION",  "text-only", ""),
    ("quality_assurance",      "Quality Control",           "QA/QC",      "text-only", ""),
    ("resource_checklist",     "Resource Checklist",        "RESOURCES",  "text-only", ""),
    ("safety_compliance",      "Compliance Checklist",      "STANDARDS",  "text-only", ""),
    ("troubleshooting",        "Troubleshooting Guide",     "SOLUTIONS",  "text-only", ""),
    ("final_verification",     "Final Verification",        "COMPLETE",   "text-only", ""),
    ("summary_checklist",      "Summary of Actions",        "SUMMARY",    "text-only", ""),
    ("call_to_action",         "Call to Action",            "NEXT STEPS", "text-only", ""),
]

# For other types, we'll use GUIDE_SECTIONS as a baseline but with different prompts
CASE_STUDY_SECTIONS = [
    ("executive_summary",      "Executive Summary",         "OVERVIEW",   "text-only", ""),
    ("client_background",      "Client Background",         "CONTEXT",    "text-only", ""),
    ("challenge_definition",   "The Challenge",             "PROBLEM",    "text-only", ""),
    ("solution_overview",      "The Solution",              "APPROACH",   "text-only", ""),
    ("implementation_detail",  "Implementation",            "PROCESS",    "text-only", ""),
    ("measurable_results",     "Measurable Results",        "OUTCOMES",   "text-only", ""),
    ("technical_innovation",   "Technical Innovation",      "EXPERTISE",  "text-only", ""),
    ("long_term_impact",       "Long-Term Impact",          "VALUE",      "text-only", ""),
    ("lessons_learned",        "Key Lessons",               "INSIGHTS",   "text-only", ""),
    ("client_testimonial",     "Client Perspective",        "FEEDBACK",   "text-only", ""),
    ("call_to_action",         "Call to Action",            "NEXT STEPS", "text-only", ""),
]

TYPE_CONFIGS = {
    "guide":             {"sections": GUIDE_SECTIONS},
    "checklist":         {"sections": CHECKLIST_SECTIONS},
    "case_study":        {"sections": CASE_STUDY_SECTIONS},
    "roi_calculator":    {"sections": GUIDE_SECTIONS},
    "trends_report":     {"sections": GUIDE_SECTIONS},
    "design_portfolio":  {"sections": GUIDE_SECTIONS},
    "client_onboarding": {"sections": GUIDE_SECTIONS},
    "custom":            {"sections": GUIDE_SECTIONS},
}

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

ALLOWED_TAGS = {
    "p", "strong", "em", "b", "i", "u",
    "h2", "h3", "h4", "h5",
    "ul", "ol", "li",
    "br", "hr",
    "blockquote", "span", "div",
    "table", "thead", "tbody", "tr", "th", "td",
    "a", "small", "mark", "code", "pre",
}

GROQ_CALL_DELAY_SECONDS = 2.0


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
    """
    Clean AI-generated HTML before injection into the PDF template.

    Steps:
      1. Convert **bold** markdown to <strong>.
      2. Remove markdown headings (# ## etc).
      3. Remove placeholder brackets like [STAT HERE].
      4. Strip any HTML tag not in ALLOWED_TAGS.
      5. Close any unclosed tags.
    """
    if not html:
        return html
    html = html.strip().strip('"')

    # Step 1: markdown bold → <strong>
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)

    # Step 2: markdown headings → remove
    html = re.sub(r'^#{1,6}\s+.*$', '', html, flags=re.MULTILINE)

    # Step 3: placeholder brackets
    html = re.sub(r'\[[A-Z][^\]]{2,80}\]', '', html)

    # Step 4: strip disallowed tags (keep allowed ones intact)
    def _handle_tag(m):
        tag = m.group(2).lower()
        if tag in ALLOWED_TAGS:
            return m.group(0)
        return ""
    html = re.sub(r'<(/?)(\w+)([^>]*)>', _handle_tag, html)

    return _ensure_closed_tags(html).strip()


def _ensure_closed_tags(html: str) -> str:
    void = {"br", "hr", "img", "input", "link", "meta"}
    stack = []
    for closing, tag in re.findall(r"<(/?)([a-zA-Z1-6]+)", html):
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


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def render_template(template: str, vars: Dict[str, Any]) -> str:
    """
    Process a Mustache-style HTML template:
      {{#if KEY}} ... {{else}} ... {{/if}}
      {{KEY}}

    Handles nested blocks correctly via recursion/repeated passes.
    """
    if not template:
        return ""

    # Pass 1: Resolve IF blocks
    changed = True
    while changed:
        changed = False
        # Match {{#if KEY}}...{{/if}} including optional {{else}}
        # This regex is simpler for the AI-side renderer
        pattern = re.compile(r'\{\{#if\s+([\w]+)\}\}(.*?)\{\{/if\}\}', re.DOTALL)
        matches = list(pattern.finditer(template))

        for m in reversed(matches):
            key = m.group(1)
            content = m.group(2)
            val = vars.get(key)

            # Check for {{else}} inside this specific block
            # We must only match {{else}} that is at the same depth
            else_pattern = re.compile(r'\{\{else\}\}')
            parts = else_pattern.split(content)

            is_truthy = False
            if val:
                if isinstance(val, str):
                    is_truthy = bool(val.strip())
                else:
                    is_truthy = True

            if is_truthy:
                # Keep part before else
                keep = parts[0]
            else:
                # Keep part after else (if it exists)
                keep = parts[1] if len(parts) > 1 else ""

            template = template[:m.start()] + keep + template[m.end():]
            changed = True

    # Pass 2: Replace variables
    def _replace_var(m):
        key = m.group(1).strip()
        val = vars.get(key)
        if val is None:
            return ""
        return str(val)

    return re.sub(r'\{\{\s*([\w]+)\s*\}\}', _replace_var, template)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION PROMPTS
# ─────────────────────────────────────────────────────────────────────────────
SECTION_PROMPTS = {

"executive_summary": """\
Write the EXECUTIVE SUMMARY for a premium guide on **{topic}** for **{audience}**.

MANDATORY STRUCTURE (follow exactly):

<p>[HOOK — Open with a provocative market reality or high-stakes fact specific to {topic}. Make {audience} feel the urgency. 80-100 words.]</p>

<p>[THE SYSTEMIC PROBLEM — Explain why {topic} is failing most {audience} today. Name the specific friction or cost they are ignoring. 120-150 words.]</p>

<p>[THE STRATEGIC OPPORTUNITY — What mastering {topic} actually unlocks. Be specific about revenue, risk, or competitive standing. 120-150 words.]</p>

<blockquote><strong>Strategic Objectives:</strong> [3-4 high-impact actions the reader will be equipped to take after reading this guide. 100-120 words.]</blockquote>

<p>[CLOSING — A powerful transition sentence leading into the Industry Analysis. 40-60 words.]</p>

BANNED: "In this guide", "Welcome", placeholders, generic advice.
Output: raw HTML only.""",

"industry_analysis": """\
Write the INDUSTRY PROBLEM ANALYSIS for a premium guide on **{topic}** for **{audience}**.

This section must demonstrate deep empathy and expertise. The reader should feel you understand their exact frustrations.
Target Audience: {audience}
Pain Points to weave in: {pain_points}

MANDATORY STRUCTURE:

<p>[THE CORE TENSION — A sophisticated opening that names the systemic friction in {topic}. Why is this a 'wicked problem' for {audience}? 100-120 words.]</p>

<h3>[Problem 1 — Economic Impact: A specific, quantifiable financial burden in {topic}]</h3>
<p>[The mechanism of this problem, how it compounds, and the hidden costs. Include realistic figures. 120-140 words.]</p>
<p><strong>Strategic Consequence:</strong> [The long-term erosion of value for {audience} if ignored. 60-80 words.]</p>

<h3>[Problem 2 — Operational Bottlenecks: A specific execution failure in {topic}]</h3>
<p>[Technical or operational complexity that stalls progress. Why traditional solutions fail. 120-140 words.]</p>
<p><strong>Strategic Consequence:</strong> [Impact on timelines and stakeholder trust. 60-80 words.]</p>

<h3>[Problem 3 — Regulatory/Compliance Friction: Specific to {topic}]</h3>
<p>[The shifting landscape of rules and standards. The cost of non-compliance. 120-140 words.]</p>
<p><strong>Strategic Consequence:</strong> [Legal and reputational risk. 60-80 words.]</p>

<h3>[Problem 4 — Stakeholder Alignment: The human element of {topic}]</h3>
<p>[Communication gaps, misaligned incentives, or resistance to change. 120-140 words.]</p>
<p><strong>Strategic Consequence:</strong> [Impact on organizational agility. 60-80 words.]</p>

<blockquote><strong>The Root Cause:</strong> [A high-level synthesis of what connects these 4 problems. What is the single shift required to fix the system? 100-120 words.]</blockquote>

BANNED: Generic problems, placeholders, "one-size-fits-all" advice.
Output: raw HTML only.""",

"core_principles": """\
Write the KEY PRINCIPLES for a premium guide on **{topic}** for **{audience}**.

These are the foundational axioms of success. Do not write tips; write governing laws of {topic}.

MANDATORY STRUCTURE:

<p>[THE PHILOSOPHY — Why these principles are non-negotiable for {audience}. What separates the 1% who master {topic} from the 99% who struggle? 100-120 words.]</p>

<h3>Principle 1: [A sophisticated, unique name for a foundational rule of {topic}]</h3>
<p>[The logic of this principle. Why it works, what it prevents, and how it challenges conventional wisdom in {topic}. 150-180 words.]</p>
<p><strong>The Implementation:</strong> [What this looks like in practice for {audience}. 60-80 words.]</p>

<h3>Principle 2: [Different dimension of {topic}]</h3>
<p>[Same high-depth format. 150-180 words.]</p>
<p><strong>The Implementation:</strong> [Same format. 60-80 words.]</p>

<h3>Principle 3: [Different dimension]</h3>
<p>[150-180 words.]</p>
<p><strong>The Implementation:</strong> [60-80 words.]</p>

<h3>Principle 4: [Different dimension]</h3>
<p>[150-180 words.]</p>
<p><strong>The Implementation:</strong> [60-80 words.]</p>

<blockquote><strong>The Master Principle:</strong> [The single unifying idea that connects all 4 principles. The ultimate takeaway for {audience} regarding {topic}. 100-120 words.]</blockquote>

BANNED: Obvious advice, placeholders, generic lists.
Output: raw HTML only.""",

"practical_strategies": """\
Write the PRACTICAL STRATEGIES for a premium guide on **{topic}** for **{audience}**.

These are the 'how-to' playbooks. They must be technical, actionable, and sophisticated.
Target Audience: {audience}
Pain Points to solve: {pain_points}

MANDATORY STRUCTURE:

<p>[THE EXECUTION GAP — Why most {audience} fail to move from strategy to results in {topic}. What is the 'last mile' problem? 100-120 words.]</p>

<h3>Strategy 1: [A high-impact, action-oriented title specific to {topic}]</h3>
<p>[A detailed, step-by-step breakdown of the execution. Name the tools, frameworks, and specific decisions required for success in {topic}. 180-220 words.]</p>
<ul>
  <li><strong>The Critical Path:</strong> [The absolute first move. 50-60 words.]</li>
  <li><strong>The Pitfall:</strong> [The most common execution mistake. 50-60 words.]</li>
  <li><strong>The Success Metric:</strong> [How {audience} will know this is working. 50-60 words.]</li>
</ul>

<h3>Strategy 2: [Different phase or dimension of {topic}]</h3>
<p>[Same high-depth format. 180-220 words.]</p>
<ul>
  <li><strong>The Critical Path:</strong> [50-60 words.]</li>
  <li><strong>The Pitfall:</strong> [50-60 words.]</li>
  <li><strong>The Success Metric:</strong> [50-60 words.]</li>
</ul>

<h3>Strategy 3: [Different phase or dimension]</h3>
<p>[Same high-depth format. 180-220 words.]</p>
<ul>
  <li><strong>The Critical Path:</strong> [50-60 words.]</li>
  <li><strong>The Pitfall:</strong> [50-60 words.]</li>
  <li><strong>The Success Metric:</strong> [50-60 words.]</li>
</ul>

<blockquote><strong>The Virtuous Cycle:</strong> [How these 3 strategies reinforce each other. What is the flywheel effect? 100-120 words.]</blockquote>

BANNED: Generic advice, "consider doing X", placeholders.
Output: raw HTML only.""",

"business_benefits": """\
Write the BUSINESS BENEFITS for a premium guide on **{topic}** for **{audience}**.

This is the business case. Every benefit must be tied to a specific financial or strategic outcome.

MANDATORY STRUCTURE:

<p>[THE VALUE PROPOSITION — A powerful opening challenging the misconception that {topic} is a cost. Why is it a high-yield investment for {audience}? 100-120 words.]</p>

<h3>[Benefit 1: Direct Financial Return — Specific to {topic}]</h3>
<p>[Explain the exact mechanism of cost saving or revenue generation. Be specific about the ROI. Include a realistic figure and unit. 180-220 words.]</p>
<p><strong>The Bottom Line:</strong> [The impact on the P&L. 60-80 words.]</p>

<h3>[Benefit 2: Operational Efficiency — Specific to {topic}]</h3>
<p>[How {topic} streamlines workflows, reduces risk, or improves performance. 180-220 words.]</p>
<p><strong>The Bottom Line:</strong> [The impact on organizational capacity. 60-80 words.]</p>

<h3>[Benefit 3: Strategic Advantage — Specific to {topic}]</h3>
<p>[How {topic} creates a competitive moat or reputational leadership for {audience}. 180-220 words.]</p>
<p><strong>The Bottom Line:</strong> [The impact on market position. 60-80 words.]</p>

<blockquote><strong>The Compounding Value:</strong> [How these 3 benefits reinforce each other to create a lasting strategic advantage. 100-120 words.]</blockquote>

BANNED: Generic benefits, placeholders, "soft" metrics without proof.
Output: raw HTML only.""",

"case_study": """\
Write a REAL WORLD CASE STUDY for a premium guide on **{topic}** for **{audience}**.

This must read like a high-stakes success story. Specific, credible, and evidence-backed.

MANDATORY STRUCTURE:

<h3>Case Study: [A sophisticated title naming a specific fictional entity, e.g. "Global Retailer Achieves 42% ROI via {topic}"]</h3>

<p><strong>The Context:</strong> [Establish the organization: Name, scale, and specific industry standing. Why were they at a breaking point regarding {topic}? 120-150 words.]</p>

<p><strong>The Crisis:</strong> [The specific technical or strategic failure that prompted action. What was at stake? 140-160 words.]</p>

<p><strong>The Intervention:</strong> [What was actually done. Name the specific framework, steps, and tools. 180-220 words.]</p>

<p><strong>The Measurable Impact:</strong> [3-4 detailed outcomes. Use specific, non-round numbers and units. 140-160 words.]</p>

<blockquote><strong>The Transferable Lesson:</strong> [The sophisticated insight from this case that {audience} must apply to their own operations. 100-120 words.]</blockquote>

BANNED: Generic stories, placeholders, "one size fits all" success.
Output: raw HTML only.""",

"risk_management": """\
Write the RISK MANAGEMENT section for a premium guide on **{topic}** for **{audience}**.

These risks must be the ones that actually hurt people in {topic} — not obvious generic risks.

MANDATORY STRUCTURE:

<p>[A deep-dive opener explaining why risk management in {topic} is different from general risk thinking — the specific technical or market nature of failure in this domain. 100-120 words.]</p>

<h3>[Risk 1: Technical/Execution — a specific failure mode in {topic} that catches experts off guard]</h3>
<p>[How it manifests, what triggers it, why even experienced {audience} miss it. 120-140 words.]</p>
<p><strong>How to prevent it:</strong> [Specific action, checklist, test, or process that neutralises this risk in {topic}. 80-100 words.]</p>

<h3>[Risk 2: Compliance/Legal — a specific regulatory or standards risk in {topic}]</h3>
<p>[What the rule requires, where people fall short, what the consequence is. 120-140 words.]</p>
<p><strong>How to prevent it:</strong> [Specific technical or administrative safeguard. 80-100 words.]</p>

<h3>[Risk 3: Commercial/Strategic — a risk that kills the business case for {topic}]</h3>
<p>[How this risk emerges, often late in the process, and why it is hard to see coming. 120-140 words.]</p>
<p><strong>How to prevent it:</strong> [Specific commercial safeguard. 80-100 words.]</p>

<blockquote><strong>The risk most people skip:</strong> [Name the single most underestimated risk in {topic} and why it gets ignored by the industry. 4-5 sentences. 100-120 words.]</blockquote>

BANNED: Generic risks like "budget overrun" or "timeline slippage" without specific causes tied to {topic}.
Output: raw HTML only.""",

"implementation_roadmap": """\
Write the IMPLEMENTATION ROADMAP section for a premium guide on **{topic}** for **{audience}**.

This is the section {audience} will screenshot and pin to their wall. Make it that useful.

MANDATORY STRUCTURE:

<p>[A detailed opener describing the most common sequencing mistake {audience} make when implementing {topic} — what they do first that they should do third. Why is order of operations critical? 100-120 words.]</p>

<h3>Phase 1: [Name specific to {topic}] — [Duration]</h3>
<p>[Detailed breakdown: What happens, who does what, what specific technical decision or deliverable marks the END of this phase. 110-130 words.]</p>

<h3>Phase 2: [Name] — [Duration]</h3>
<p>[110-130 words. Different from Phase 1.]</p>

<h3>Phase 3: [Name] — [Duration]</h3>
<p>[110-130 words.]</p>

<h3>Phase 4: [Name] — [Duration]</h3>
<p>[110-130 words.]</p>

<h3>Phase 5: [Name] — [Duration]</h3>
<p>[110-130 words.]</p>

<h3>Phase 6: [Name] — [Duration]</h3>
<p>[110-130 words.]</p>

<blockquote><strong>The milestone that matters most:</strong> [A deep analysis of the single phase transition in {topic} implementation where most projects either succeed or fail permanently — and what makes the difference. 80-100 words.]</blockquote>

BANNED: Phases named "Planning", "Execution", "Review" — too generic. Each phase name must reflect something specific about how {topic} actually works.
Output: raw HTML only.""",

"future_trends": """\
Write the FUTURE TRENDS section for a premium guide on **{topic}** for **{audience}**.

These trends must be specific to {topic} — not generic "AI will change everything" statements.

MANDATORY STRUCTURE:

<p>[A visionary opener describing the single biggest paradigm shift happening in {topic} right now that most {audience} are underestimating. 100-120 words.]</p>

<h3>[Trend 1 — name it specifically, tied to {topic}]</h3>
<p>[What is driving this trend in {topic}. What it will change. When. What {audience} should do in the next 12 months to prepare. Include a specific market signal or technical timeline. 140-160 words.]</p>

<h3>[Trend 2 — different force in {topic}]</h3>
<p>[Same detailed format. 140-160 words.]</p>

<h3>[Trend 3 — different force]</h3>
<p>[140-160 words.]</p>

<h3>[Trend 4 — different force]</h3>
<p>[140-160 words.]</p>

<blockquote><strong>The trend to act on now:</strong> [Which of the 4 trends has the shortest window before it becomes table stakes in {topic} — and the specific cost of waiting. 4-5 sentences. 100-120 words.]</blockquote>

BANNED: Trends that are already mainstream. Trends not specific to {topic}. Generic "digital transformation" or "AI disruption" without specific connection to {topic}.
Output: raw HTML only.""",

"key_takeaways": """\
Write the KEY TAKEAWAYS section for a premium guide on **{topic}** for **{audience}**.

This is the last section before the CTA. It must crystallise everything and create momentum.

MANDATORY STRUCTURE:

<p>[A sophisticated opener that frames the transition from reader to practitioner of {topic}. 80-100 words.]</p>

<ul>
  <li><strong>[Takeaway 1 label — from the challenges section]:</strong> [The most important insight about what makes {topic} hard. 80-100 words. Specific. Memorable.]</li>
  <li><strong>[Takeaway 2 label — from the strategies section]:</strong> [The most actionable thing to do about {topic} starting tomorrow. 80-100 words.]</li>
  <li><strong>[Takeaway 3 label — from the risks section]:</strong> [The most important thing to avoid or protect in {topic}. 80-100 words.]</li>
  <li><strong>[Takeaway 4 label — from the benefits section]:</strong> [The financial or strategic case for {topic} in one clear, powerful statement. 80-100 words.]</li>
  <li><strong>[Takeaway 5 label — from the trends section]:</strong> [What changes if {audience} waits 12 months to act on {topic}. 80-100 words.]</li>
</ul>

<blockquote><strong>The one thing:</strong> [If the reader only does one thing after reading this guide, what should it be? Make it concrete, high-impact, and specific to {topic}. 4-5 sentences. 100-120 words.]</blockquote>

<p>[Closing transition — A powerful closing paragraph that naturally leads the reader to the CTA. Create a sense of partnership and readiness. 100-120 words.]</p>

BANNED: Vague takeaways like "sustainable architecture is important". Every takeaway must contain a specific, actionable or protective insight.
Output: raw HTML only.""",

"call_to_action": """\
Write the CALL TO ACTION for a premium guide on **{topic}** for **{audience}**.

This is the conversion point. It must feel like an invitation from a peer, not a sales pitch.

MANDATORY STRUCTURE:

<h3>[A strategic heading that speaks to the transition from insight to execution for {topic}]</h3>
<p>[The Value Realization: Acknowledge the reader's new expertise. Why is the 'last mile' of implementation where {audience} actually wins or loses in {topic}? 140-160 words.]</p>

<h3>The First 90 Days: A Strategic Partnership</h3>
<p>[Describe the immediate path forward. What technical or strategic roadblocks in {topic} will we solve together? What is the tangible deliverable of the first session? 140-160 words.]</p>

<h3>The Cost of Inaction</h3>
<p>[A detailed analysis of the opportunity cost of delay. Reference specific market, technical, or regulatory pressures in {topic}. 120-140 words.]</p>

<blockquote><strong>The Path Forward:</strong> [A clear, professional next step. Explain exactly what happens after they take this action. Use the provided action if it's real, otherwise infer a premium consultation: {call_to_action}. 60-80 words.]</blockquote>

BANNED: Sales clichés, "Contact us today", placeholders, generic calls.
Output: raw HTML only.""",
}


# ─────────────────────────────────────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────────────────────────────────────

# Mapping of section keys to their corresponding image variable in templates (e.g., guide.html)
SECTION_IMAGE_MAP = {
    "executive_summary": "image_1_url",
    "core_principles": "image_2_url",
    "business_benefits": "image_3_url",
    "risk_management": "image_4_url",
    "future_trends": "image_5_url",
}

class GroqClient:
    GUIDE_SECTIONS   = GUIDE_SECTIONS
    DOC_TYPE_LABELS  = DOC_TYPE_LABELS
    TYPE_CONFIGS     = TYPE_CONFIGS
    _TYPE_MAP        = _TYPE_MAP

    # For backwards compatibility where code expects .SECTIONS (defaults to guide)
    SECTIONS         = GUIDE_SECTIONS
    SECTION_KEYS     = [s[0] for s in GUIDE_SECTIONS]

    def __init__(self, api_key: str = None):
        # 1. Groq Client (Primary)
        groq_api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        self.groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
        if not self.groq_client:
            logger.warning("⚠️ GROQ_API_KEY is not set.")

        # 2. Anthropic Client (Fallback 1)
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key) if anthropic_api_key else None
        if not self.anthropic_client:
            logger.info("ℹ️ ANTHROPIC_API_KEY is not set (optional fallback).")

        # 3. OpenAI Client (Fallback 2)
        openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = openai.OpenAI(api_key=openai_api_key) if openai_api_key else None
        if not self.openai_client:
            logger.info("ℹ️ OPENAI_API_KEY is not set (optional fallback).")

        # 4. Google Client (Fallback 3)
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            genai.configure(api_key=google_api_key)
            self.google_model = genai.GenerativeModel(AI_CONFIGS["google"]["model"])
        else:
            self.google_model = None
            logger.info("ℹ️ GOOGLE_API_KEY is not set (optional fallback).")

        # Backwards compatibility
        self.client      = self.groq_client
        self.model       = AI_CONFIGS["groq"]["model"]
        self.temperature = 0.72
        self.max_tokens  = AI_CONFIGS["groq"]["max_tokens"]

    def _call_ai_with_fallback(self, system_msg: str, user_msg: str, temperature: float = 0.72) -> Tuple[str, int]:
        """
        Executes AI call with automatic fallback logic across 4 providers.
        Attempts Groq (70B) -> Groq (8B) -> Anthropic -> OpenAI -> Google.
        Returns (content, tokens_used).
        """
        providers = [
            ("groq",          self.groq_client),
            ("groq_fallback", self.groq_client),
            ("anthropic",     self.anthropic_client),
            ("openai",        self.openai_client),
            ("google",        self.google_model)
        ]

        errors = []
        for name, client in providers:
            if not client:
                logger.debug(f"  ⏭️ Skipping {name} (API key not configured)")
                continue

            try:
                config = AI_CONFIGS[name]
                logger.info(f"  → Calling {name} ({config['model']})…")

                if name in ("groq", "groq_fallback"):
                    try:
                        resp = client.chat.completions.create(
                            model=config["model"],
                            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                            temperature=temperature,
                            max_tokens=config["max_tokens"],
                        )
                        content = resp.choices[0].message.content.strip()
                        tokens = getattr(resp.usage, "total_tokens", 0) if hasattr(resp, "usage") else 0
                        if content:
                            logger.info(f"  ✅ {name} succeeded ({len(content)} chars, {tokens} tokens)")
                            return content, tokens
                        else:
                            logger.warning(f"  ⚠️ {name} returned empty content")
                    except Exception as ge:
                        if "429" in str(ge) and "tokens per day" in str(ge).lower():
                            err_msg = f"Groq daily token limit reached for model {config['model']}."
                            logger.warning(f"  ❌ {name} rate limit: {err_msg}")
                            errors.append(f"{name}: {err_msg}")
                            continue # Try next provider
                        raise ge

                elif name == "anthropic":
                    resp = client.messages.create(
                        model=config["model"],
                        system=system_msg,
                        messages=[{"role": "user", "content": user_msg}],
                        temperature=temperature,
                        max_tokens=config["max_tokens"],
                    )
                    content = resp.content[0].text.strip()
                    tokens = getattr(resp.usage, "input_tokens", 0) + getattr(resp.usage, "output_tokens", 0) if hasattr(resp, "usage") else 0
                    if content:
                        logger.info(f"  ✅ {name} succeeded ({len(content)} chars, {tokens} tokens)")
                        return content, tokens
                    else:
                        logger.warning(f"  ⚠️ {name} returned empty content")

                elif name == "openai":
                    resp = client.chat.completions.create(
                        model=config["model"],
                        messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                        temperature=temperature,
                        max_tokens=config["max_tokens"],
                    )
                    content = resp.choices[0].message.content.strip()
                    tokens = getattr(resp.usage, "total_tokens", 0) if hasattr(resp, "usage") else 0
                    if content:
                        logger.info(f"  ✅ {name} succeeded ({len(content)} chars, {tokens} tokens)")
                        return content, tokens
                    else:
                        logger.warning(f"  ⚠️ {name} returned empty content")

                elif name == "google":
                    prompt = f"SYSTEM: {system_msg}\n\nUSER: {user_msg}"
                    resp = client.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=config["max_tokens"],
                            temperature=temperature,
                        )
                    )
                    content = resp.text.strip()
                    # Gemini doesn't always provide simple usage in the same way, estimation or skipping for now
                    tokens = 0 # Placeholder for Google usage
                    if content:
                        logger.info(f"  ✅ {name} succeeded ({len(content)} chars)")
                        return content, tokens
                    else:
                        logger.warning(f"  ⚠️ {name} returned empty content")

            except Exception as e:
                # Log the detailed error message for troubleshooting
                err_msg = str(e)
                logger.warning(f"  ❌ {name} failed: {err_msg}")
                errors.append(f"{name}: {err_msg}")
                continue

        # If we reach here, all configured providers failed
        if not errors:
            raise RuntimeError("No AI providers configured (missing API keys)")
        
        raise RuntimeError(f"All AI providers failed: {'; '.join(errors)}")

    # ──────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, Any]:
        raw_type = str(
            user_answers.get("document_type") or
            user_answers.get("lead_magnet_type") or "guide"
        ).strip()
        
        # Strict mapping for absolute type fidelity
        doc_type = _TYPE_MAP.get(raw_type.lower().replace("-","_").replace(" ","_"), "guide")
        if doc_type not in TYPE_CONFIGS:
            doc_type = "guide"

        pp = user_answers.get("pain_points")
        if pp is None or (isinstance(pp, list) and len(pp) == 0):
            pp = user_answers.get("audience_pain_points", [])
        pain_points = pp if isinstance(pp, list) else ([pp] if pp else [])
        audience    = user_answers.get("target_audience", "Stakeholders")
        
        # 🚀 PLACEHOLDER SANITIZATION: Detect and remove "hhhh" style placeholders
        # If CTA or Desired Outcome is garbage, we set it to empty so the AI can infer better ones.
        def _is_placeholder(s: str) -> bool:
            if not s: return False
            s = s.strip().lower()
            # Detect repeated characters (e.g., "hhhh", "xxxx") or very short strings
            if len(s) > 0 and len(set(s)) == 1 and len(s) > 3: return True
            if s in ("test", "test message", "xxx", "abc", "asdf"): return True
            return False

        desired_outcome = str(user_answers.get("desired_outcome", "") or "").strip()
        if _is_placeholder(desired_outcome): desired_outcome = ""

        call_to_action = str(user_answers.get("call_to_action", "") or "").strip()
        if _is_placeholder(call_to_action): call_to_action = ""

        return {
            "topic":           _clean_topic_slug(str(user_answers.get("main_topic", "Strategic Design"))),
            "audience":        ", ".join(audience) if isinstance(audience, list) else str(audience),
            "pain_points":     ", ".join(pain_points) if isinstance(pain_points, list) else str(pain_points),
            "psychographics":  str(user_answers.get("psychographics", "")).strip(),
            "firm_usp":        str(user_answers.get("firm_usp", "")).strip(),
            "desired_outcome": desired_outcome,
            "call_to_action":  call_to_action,
            "special_requests": str(user_answers.get("special_requests", "") or "").strip(),
            "tone":            user_answers.get("tone", "Professional"),
            "industry":        user_answers.get("industry", ""),
            "document_type":   doc_type,
        }

    def generate_lead_magnet_json(
        self, signals: Dict[str, Any], firm_profile: Dict[str, Any], on_token_update: Optional[callable] = None
    ) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError(
                "Groq is not configured: set the GROQ_API_KEY environment variable."
            )

        doc_type    = signals.get("document_type", "guide")
        type_config = TYPE_CONFIGS.get(doc_type) or TYPE_CONFIGS["guide"]
        sections    = type_config["sections"]
        type_label  = DOC_TYPE_LABELS.get(doc_type) or DOC_TYPE_LABELS["guide"]
        
        topic       = signals["topic"]
        audience    = signals["audience"]
        pain_points = signals.get("pain_points", "")
        firm_usp    = signals.get("firm_usp", "")
        desired_outcome  = str(signals.get("desired_outcome", "") or "").strip()
        call_to_action   = str(signals.get("call_to_action", "") or "").strip()
        special_requests = str(signals.get("special_requests", "") or "").strip()

        logger.info(f"🚀 Type-Strict Generation | type={doc_type} | topic={topic[:40]}")

        total_tokens = 0

        # ── Pass 1a: Title ─────────────────────────────────────────────────
        title    = ""
        subtitle = ""
        try:
            system_prompt = (
                f"You are a world-class McKinsey-style consultant and professional copywriter. "
                f"You write authoritative, high-impact titles for a PREMIUM {type_label.upper()} on '{topic}'.\n\n"
                "Respond with EXACTLY two lines:\n"
                "TITLE: [A sophisticated 3-6 word title that sounds like a $100k strategic report]\n"
                "SUBTITLE: [A compelling one-sentence value proposition that targets the audience's deepest needs]"
            )
            user_prompt = (
                f"Topic: '{topic}' | Audience: {audience} | Type: {type_label}\n"
                f"Pain Points: {pain_points}\n"
                f"Desired Outcome: {desired_outcome}\n"
                f"RULES: Zero marketing fluff. No placeholders. Must feature '{topic}' prominently."
            )
            raw_title_resp, title_tokens = self._call_ai_with_fallback(system_prompt, user_prompt, temperature=0.7)
            total_tokens += title_tokens
            if on_token_update:
                on_token_update(total_tokens)

            for line in raw_title_resp.split("\n"):
                if line.upper().startswith("TITLE:"):
                    title = line.split(":", 1)[1].strip()
                elif line.upper().startswith("SUBTITLE:"):
                    subtitle = line.split(":", 1)[1].strip()
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")

        # ── Pass 1b: Per-section generation ───────────────────────────────
        system_msg = (
            f"You are a premium content strategist writing one section of a {type_label.upper()} on '{topic}' for {audience}.\n\n"
            "CRITICAL QUALITY RULES:\n"
            f"1. NO PLACEHOLDERS: Never use 'hhhh', 'test', or any filler. Infer deeply relevant content based on '{topic}'.\n"
            f"2. DEEP SPECIFICITY: Every sentence must be specific to '{topic}' and {audience}. Zero generic business advice.\n"
            f"3. VALUE DENSITY: Use fewer tokens by eliminating fluff. Every word must add value. Avoid repetitive transitions.\n"
            f"4. AUDIENCE-CENTRIC: Address {audience} segments by name. Show how {topic} impacts them differently.\n"
            f"5. PAIN POINT INTEGRATION: Weave these pain points into the narrative: {pain_points}.\n"
            "6. CREDIBLE DATA: Use realistic statistics with specific numbers and units (e.g., '34.2% reduction').\n"
            "7. RAW HTML ONLY: Use <h3>, <p>, <strong>, <ul>/<li>, and <blockquote>. No markdown.\n"
            "8. COMPLETION: Sections must end with a full, impactful thought. NEVER truncate.\n"
            "9. NO IMAGES: Do not include any <img> tags."
        )

        sections_content: Dict[str, str] = {}

        for idx, (key, default_title, default_label, _, _) in enumerate(sections):
            if idx > 0:
                logger.debug(f"  ⏳ Rate-limit pause ({GROQ_CALL_DELAY_SECONDS}s)…")
                time.sleep(GROQ_CALL_DELAY_SECONDS)

            # Check if this section has an image slot and if an image URL is provided
            image_slot = SECTION_IMAGE_MAP.get(key)
            has_image = bool(firm_profile.get(image_slot)) if image_slot else False
            
            # Adjust target word count to fill the page perfectly based on image presence
            # A4 page with 15.5px font: ~550 words without image, ~350 words with image.
            target_words = "350-400" if has_image else "550-600"
            if has_image:
                logger.info(f"  🖼️ Section {key} has an image. Adjusting target to {target_words} words.")

            # Try type-specific prompt first, then fallback to general
            prompt_template = SECTION_PROMPTS.get(f"{doc_type}_{key}") or SECTION_PROMPTS.get(key, "")
            
            if not prompt_template:
                # Construct a strict type-aware fallback prompt
                prompt_template = f"Write a comprehensive {default_title} for this {type_label}. Focus on high-value insights for {audience} regarding {topic}."

            try:
                section_prompt = prompt_template.format(
                    topic=topic, audience=audience,
                    pain_points=pain_points, firm_usp=firm_usp,
                    lead_magnet_type=type_label,
                    desired_outcome=desired_outcome,
                    call_to_action=call_to_action,
                )
            except (KeyError, IndexError):
                section_prompt = prompt_template

            user_msg = (
                f"DOCUMENT TYPE: {type_label.upper()}\n"
                f"TOPIC: {topic}\n"
                f"AUDIENCE: {audience}\n"
                f"PAIN POINTS: {pain_points}\n"
                f"DESIRED OUTCOME: {desired_outcome}\n"
                f"CALL TO ACTION: {call_to_action}\n"
                f"SPECIAL REQUESTS: {special_requests}\n\n"
                f"WRITE SECTION: {default_title}\n\n"
                f"{section_prompt}\n\n"
                f"CRITICAL: This is for a {type_label.upper()}. Ensure content matches this format perfectly. "
                f"TARGET {target_words} words for this section to ensure the page is perfectly filled. Raw HTML only. No <img> tags."
            )

            try:
                raw, tokens = self._call_ai_with_fallback(system_msg, user_msg, temperature=self.temperature)
                total_tokens += tokens
                if on_token_update:
                    on_token_update(total_tokens)
                raw = re.sub(r'^```html?\s*', '', raw, flags=re.IGNORECASE)
                raw = re.sub(r'\s*```\s*$', '', raw)
                raw = _sanitize_html(raw)

                if len(_html_to_text(raw)) < 50:
                    logger.warning(f"  ⚠️ Section {key} too short, retrying...")
                    raw, tokens = self._call_ai_with_fallback(system_msg, user_msg, temperature=min(self.temperature + 0.1, 0.9))
                    total_tokens += tokens
                    raw = _sanitize_html(raw)

                sections_content[key] = raw
                logger.info(f"  ✅ {key}: {len(sections_content[key])} chars")
            except Exception as e:
                logger.error(f"  ❌ {key} failed all providers: {e}")
                
                # 🚀 NO-FALLBACK POLICY: If all AI providers fail, we throw an error.
                # The user explicitly requested NO hardcoded/fallback/filler text.
                # We only keep a minimal log of what went wrong.
                raise RuntimeError(f"Section '{key}' failed to generate after trying all AI providers. {e}")

        section_keys = [s[0] for s in sections]
        filled = sum(1 for k in section_keys if len(sections_content.get(k, "")) > 100)
        logger.info(f"✅ Complete | {filled}/{len(section_keys)} sections filled | Total tokens: {total_tokens}")

        return {
            "title":               title,
            "subtitle":            subtitle,
            "document_type":       doc_type,
            "document_type_label": type_label,
            "tokens_used":         total_tokens,
            "sections": {
                key: {"content": sections_content.get(key, ""), "title": dtitle, "label": dlabel}
                for key, dtitle, dlabel, *_ in sections
            },
        }

    def normalize_ai_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        sections_data = raw.get("sections", {})
        doc_type      = raw.get("document_type", "guide")
        type_config   = TYPE_CONFIGS.get(doc_type) or TYPE_CONFIGS["guide"]
        sections      = type_config["sections"]

        normalized: Dict[str, Any] = {
            "title":               raw.get("title") or "",
            "subtitle":            raw.get("subtitle", ""),
            "document_type":       doc_type,
            "document_type_label": raw.get("document_type_label") or "",
            "framework":           {},
        }

        # Per-section normalization with POSITIONAL COMPATIBILITY
        # This ensures that if we generate a Case Study with its own keys,
        # it still maps to the GUIDE_SECTIONS keys used in the main template.
        for idx, (key, default_title, default_label, _, _) in enumerate(sections):
            sec_data = sections_data.get(key, {})
            content  = sec_data.get("content", "") if isinstance(sec_data, dict) else str(sec_data)
            title    = (sec_data.get("title", "") if isinstance(sec_data, dict) else "") or default_title

            sanitized_content = _sanitize_html(str(content))
            normalized[key] = sanitized_content
            normalized["framework"][key] = {"title": title or default_title, "kicker": default_label}

            # Map to positional keys for template compatibility
            if idx < len(GUIDE_SECTIONS):
                guide_key = GUIDE_SECTIONS[idx][0]
                normalized[guide_key] = sanitized_content
                normalized["framework"][guide_key] = {"title": title or default_title, "kicker": default_label}

        normalized["summary"]              = normalized.get("executive_summary", "")[:500]
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
        doc_type = ai_content.get("document_type", "guide")
        type_config = TYPE_CONFIGS.get(doc_type) or TYPE_CONFIGS["guide"]
        sections = type_config["sections"]

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
        subtitle = (
            _clean_topic_slug(raw_sub)
            if raw_sub and raw_sub.strip().lower() != topic.strip().lower()
            else ""
        )
        doc_type_label = ai_content.get("document_type_label") or ""

        cta_html     = ai_content.get("call_to_action", "")
        h3_match     = re.search(r'<h3>(.*?)</h3>', cta_html)
        cta_headline = _html_to_text(h3_match.group(1)) if h3_match else ""

        tvars: Dict[str, Any] = {
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
            "documentType":      doc_type,
            "documentTypeLabel": doc_type_label,
            "mainTitle":         ai_content.get("title") or topic,
            "documentSubtitle":  subtitle or f"A comprehensive {doc_type} for {signals.get('target_audience', 'professionals')}",
            # Company
            "companyName":  company_name,
            "emailAddress": work_email,
            "phoneNumber":  firm_profile.get("phone_number", ""),
            "website":      firm_profile.get("firm_website", ""),
            "logoUrl":      firm_profile.get("firm_logo") or firm_profile.get("logo_url") or "",
            # Labels
            "contentsTitle": "Table of Contents",
            "ctaHeadline":   cta_headline,
            "termsTitle":    "Terms of Use & Disclaimer",
            # Terms
            "termsSummary":    ai_content.get("legal_notice_summary", ""),
            "termsParagraph1": f"© {company_name}. All rights reserved.",
            "termsParagraph2": f"The information in this {doc_type_label} relates to {topic} and does not constitute legal, financial, or professional advice.",
            "termsParagraph3": "Readers are advised to verify all information independently before making project or business decisions.",
            "termsParagraph4": "",
            "termsParagraph5": "",
        }

        # Image slots
        for i in range(1, 7):
            url = str(firm_profile.get(f"image_{i}_url") or "").strip()
            if url:
                tvars[f"image_{i}_url"] = url

        # TOC
        toc_parts = []
        for idx, (key, default_title, _, _, _) in enumerate(sections):
            fw    = ai_content.get("framework", {}).get(key, {})
            title = fw.get("title") or default_title
            page  = str(idx + 4).zfill(2)
            toc_parts.append(
                f'<div class="toc-item">'
                f'<span class="toc-num">{str(idx + 1).zfill(2)}</span>'
                f'<span class="toc-label">{title}</span>'
                f'<span class="toc-dots"></span>'
                f'<span class="toc-pg">{page}</span>'
                f'</div>'
            )
        tvars["toc_sections_html"] = "\n".join(toc_parts)
        tvars["toc_html"]          = tvars["toc_sections_html"]

        # Per-section vars
        for idx, (key, default_title, default_label, _, _) in enumerate(sections):
            fw      = ai_content.get("framework", {}).get(key, {})
            title   = fw.get("title") or default_title
            content = ai_content.get(key, "")
            s_idx   = idx + 1

            tvars[f"customTitle{s_idx}"]          = title
            tvars[f"section_{key}_full_html"]      = content
            tvars[f"section_{key}_id"]             = f"section-{key}"
            tvars[f"section_{key}_title"]          = title
            tvars[f"section_{key}_kicker"]         = default_label
            tvars[f"section_{key}_kicker_label"]   = default_label
            tvars[f"section_{key}_intro"]          = self._extract_intro_text(content)
            tvars[f"section_{key}_support"]        = self._extract_support_text(content)
            sv, sl = self._extract_stat(content)
            tvars[f"section_{key}_stat_val"]       = sv
            tvars[f"section_{key}_stat_lbl"]       = sl
            tvars[f"section_{key}_bullets_html"]   = self._extract_bullets_html(content)

        for n in range(2, 20): # Increased range for potential longer docs
            tvars[f"pageNumber{n}"]       = str(n).zfill(2)
            tvars[f"pageNumberHeader{n}"] = str(n).zfill(2)

        return tvars

    def render_html(self, template: str, vars: Dict[str, Any]) -> str:
        return render_template(template, vars)

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
        return text[:end + 1] if end > max_chars // 2 else trunc.rstrip() + "…"

    def _extract_support_text(self, html: str, max_chars: int = 400) -> str:
        if not html: return ""
        paras = re.findall(r'<p>(.*?)</p>', html, re.S)
        if len(paras) <= 1: return ""
        combined = " ".join(_html_to_text(p) for p in paras[1:3])
        if len(combined) <= max_chars: return combined
        trunc = combined[:max_chars]
        end   = max(trunc.rfind('.'), trunc.rfind('!'), trunc.rfind('?'))
        return combined[:end + 1] if end > max_chars // 2 else trunc.rstrip() + "…"

    def _extract_bullets_html(self, html: str) -> str:
        items = re.findall(r'<li>(.*?)</li>', html, re.S)
        if not items:
            items = [re.sub(r'<[^>]+>', ' ', h).strip() for h in re.findall(r'<h3>(.*?)</h3>', html)]
        return "".join(f"<li>{_html_to_text(it)}</li>" for it in items[:5])

    def _extract_stat(self, html: str) -> Tuple[str, str]:
        return ("", "")

    def ensure_section_content(self, sections, signals, firm_profile):
        return sections
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

# FIX 1: Expanded ALLOWED_TAGS — previously stripped div/table/a/etc., causing LLM
# output to fail the 50-char validation check and trigger the fallback error message.
ALLOWED_TAGS = {
    "p", "strong", "em", "b", "i", "u",
    "h2", "h3", "h4", "h5",
    "ul", "ol", "li",
    "br", "hr",
    "blockquote", "span", "div",
    "table", "thead", "tbody", "tr", "th", "td",
    "a", "small", "mark", "code", "pre",
}

# FIX 2: Rate limiting — Groq free tier throttles llama-3.3-70b-versatile hard.
# 11 back-to-back calls without delay = rate limit errors after the first 1-2 calls.
# This caused 10/11 sections to fall back to placeholder text.
GROQ_CALL_DELAY_SECONDS = 2.5   # pause between each section call


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
    # Convert markdown bold to HTML strong
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    # Remove markdown headings
    html = re.sub(r'^#{1,6}\s+.*$', '', html, flags=re.MULTILINE)
    # Remove bracketed placeholder text like [INSERT STAT]
    html = re.sub(r'\[[A-Z][^\]]{2,80}\]', '', html)
    # FIX 3: Strip disallowed tags but KEEP their inner text.
    # Previously the lambda returned "" for the whole tag including text content,
    # which caused valid LLM output to shrink below the 50-char threshold.
    def _handle_tag(m):
        tag = m.group(2).lower()
        if tag in ALLOWED_TAGS:
            return m.group(0)
        return ""   # remove only the tag token; text nodes between tags are untouched
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
# FIX 4: This was completely missing. The renderer was passing the raw template
# string to PrinceXML with all {{#if}}...{{/if}} blocks unprocessed, causing
# them to appear as literal text in the PDF (including as whole blank pages
# when {{/if}} fell on a page boundary).
# ─────────────────────────────────────────────────────────────────────────────

def render_template(template: str, vars: Dict[str, Any]) -> str:
    """
    Process a Handlebars-style HTML template:
      {{#if KEY}} ... {{/if}}  →  include block only when vars[KEY] is truthy
      {{KEY}}                  →  substitute vars[KEY] (empty string if missing)

    Handles up to 5 levels of nesting via repeated passes.
    Must be called BEFORE passing HTML to PrinceXML / WeasyPrint.

    Usage:
        template_str = open("Template.html").read()
        vars = client.map_to_template_vars(ai_content, firm_profile, signals)
        rendered_html = render_template(template_str, vars)
        # → pass rendered_html to your PDF renderer
    """
    # --- Pass 1-5: resolve {{#if KEY}}...{{/if}} blocks (innermost first) ---
    for _ in range(5):
        # Use a factory to avoid the Python closure-in-loop capture bug:
        # each iteration binds the current `vars` dict snapshot correctly.
        def _make_replacer(v):
            def _replace_if(m):
                key     = m.group(1).strip()
                content = m.group(2)
                return content if v.get(key) else ""
            return _replace_if

        new_html = re.sub(
            r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}',
            _make_replacer(vars),
            template,
            flags=re.DOTALL,
        )
        if new_html == template:
            break
        template = new_html

    # --- Pass 2: substitute remaining {{VAR}} placeholders ---
    def _replace_var(m):
        key = m.group(1).strip()
        val = vars.get(key)
        return "" if val is None else str(val)

    return re.sub(r'\{\{(\w+)\}\}', _replace_var, template)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION PROMPTS
# ─────────────────────────────────────────────────────────────────────────────
SECTION_PROMPTS = {

"executive_summary": """\
Write the EXECUTIVE SUMMARY section for a premium guide on **{topic}** for **{audience}**.

MANDATORY STRUCTURE (follow exactly):

<p>[HOOK — open with a single provocative fact or market reality specific to {topic}. Not "In this guide". Not "Welcome". A fact that makes {audience} stop and pay attention. 40-60 words.]</p>

<p>[THE PROBLEM — why {topic} is harder than most {audience} realise right now. Name the specific friction, cost, or consequence they are likely experiencing. Reference a real market condition or constraint. 100-120 words.]</p>

<p>[THE OPPORTUNITY — what mastering {topic} actually unlocks. Be specific: cost saved, revenue gained, risk avoided, competitive position improved. Name a concrete outcome. 100-120 words.]</p>

<blockquote><strong>What this guide delivers:</strong> [3-4 specific things the reader will be able to DO after reading — not "understand" or "learn about" — actual actions they can take on {topic}.]</blockquote>

<p>[CLOSING — one sentence that makes the reader want to turn the page. Reference the first section they are about to read.]</p>

BANNED: "In this guide...", "It is important to note...", "our firm", "we believe", any sentence that could apply to a different topic.
Output: raw HTML only.""",

"industry_analysis": """\
Write the INDUSTRY PROBLEM ANALYSIS section for a premium guide on **{topic}** for **{audience}**.

This section must make the reader feel SEEN — like you understand their exact frustrations with {topic}.
Pain points to address: {pain_points}

MANDATORY STRUCTURE:

<p>[1-2 sentence opener that names the core tension in {topic} without being generic. 30-50 words.]</p>

<h3>[Problem 1 — Financial/Cost: a specific cost problem in {topic}]</h3>
<p>[What triggers this problem, how it compounds, what it actually costs. 80-100 words. Include a realistic figure.]</p>
<p><strong>Why this matters:</strong> [The downstream consequence for {audience} if this goes unaddressed. 40-60 words.]</p>

<h3>[Problem 2 — Execution/Technical: a specific doing problem in {topic}]</h3>
<p>[The specific operational or technical failure mode. What people try and why it fails. 80-100 words.]</p>
<p><strong>Why this matters:</strong> [Consequence. 40-60 words.]</p>

<h3>[Problem 3 — Compliance/Standards: a specific rules or requirements problem in {topic}]</h3>
<p>[What the regulation/standard requires, where people fall short, what it costs to get wrong. 80-100 words.]</p>
<p><strong>Why this matters:</strong> [Consequence. 40-60 words.]</p>

<h3>[Problem 4 — People/Stakeholder: a specific communication or alignment problem in {topic}]</h3>
<p>[The human side of the problem — misaligned expectations, knowledge gaps, trust failures. 80-100 words.]</p>
<p><strong>Why this matters:</strong> [Consequence. 40-60 words.]</p>

<blockquote><strong>The pattern:</strong> [A 2-3 sentence observation about what connects all 4 problems — the underlying root cause in {topic} that, if fixed, fixes most of the rest.]</blockquote>

BANNED: Generic problems that could apply to any industry. Every problem must be specific to {topic}.
Output: raw HTML only.""",

"core_principles": """\
Write the KEY PRINCIPLES section for a premium guide on **{topic}** for **{audience}**.

These are not tips. These are the non-negotiable foundations that separate people who get results in {topic} from those who don't.

MANDATORY STRUCTURE:

<p>[Opener: why these principles exist — what happens to {audience} who skip them. 50-70 words. Specific to {topic}.]</p>

<h3>Principle 1: [Name — make it memorable, specific to {topic}]</h3>
<p>[What this principle means in practice for {topic}. The insight behind it. What it looks like when followed vs ignored. Include a real-world implication. 90-110 words.]</p>

<h3>Principle 2: [Different dimension of {topic}]</h3>
<p>[Same format. Different domain. 90-110 words.]</p>

<h3>Principle 3: [Different dimension]</h3>
<p>[90-110 words.]</p>

<h3>Principle 4: [Different dimension]</h3>
<p>[90-110 words.]</p>

<blockquote><strong>The master principle:</strong> [One sentence that ties all 4 together — the single idea that, if a {audience} only remembered one thing from this section, what would it be?]</blockquote>

BANNED: Principles that are obvious or generic. Each must teach something that a professional in {topic} might not already know.
Output: raw HTML only.""",

"practical_strategies": """\
Write the PRACTICAL STRATEGIES section for a premium guide on **{topic}** for **{audience}**.

These strategies must be immediately actionable. Not theory. Not "consider doing X". Specific steps.
Pain points: {pain_points}

MANDATORY STRUCTURE:

<p>[Opener: why most approaches to {topic} fail — the mistake that makes strategies useless. 40-60 words.]</p>

<h3>Strategy 1: [Action-verb title — what to DO, specific to {topic}]</h3>
<p>[How to execute this. Name the specific steps, tools, or methods. What it looks like in practice for {audience} working on {topic}. 100-120 words.]</p>
<ul>
  <li><strong>Do this first:</strong> [The single most important first action.]</li>
  <li><strong>Watch out for:</strong> [The specific mistake that kills this strategy in {topic}.]</li>
  <li><strong>You know it's working when:</strong> [A measurable signal of success.]</li>
</ul>

<h3>Strategy 2: [Different phase or dimension of {topic}]</h3>
<p>[100-120 words.]</p>
<ul>
  <li><strong>Do this first:</strong> [First action.]</li>
  <li><strong>Watch out for:</strong> [Specific mistake.]</li>
  <li><strong>You know it's working when:</strong> [Success signal.]</li>
</ul>

<h3>Strategy 3: [Different phase or dimension]</h3>
<p>[100-120 words.]</p>
<ul>
  <li><strong>Do this first:</strong> [First action.]</li>
  <li><strong>Watch out for:</strong> [Specific mistake.]</li>
  <li><strong>You know it's working when:</strong> [Success signal.]</li>
</ul>

<blockquote><strong>The sequence that works:</strong> [A 2-sentence summary of how these 3 strategies chain together — when to use each one relative to the others in {topic}.]</blockquote>

BANNED: Vague advice. "Consider...", "You might want to...", "It is recommended that...". Every strategy must tell the reader exactly what to do.
Output: raw HTML only.""",

"business_benefits": """\
Write the BUSINESS BENEFITS section for a premium guide on **{topic}** for **{audience}**.

This section must make the business case so clearly that a {audience} could use it to justify investment in {topic} to a decision-maker.

MANDATORY STRUCTURE:

<p>[Opener: the single biggest misconception about what {topic} actually costs vs what it returns. 50-70 words.]</p>

<h3>[Benefit 1: Financial — specific return, saving, or revenue impact from {topic}]</h3>
<p>[Explain exactly how {topic} generates this financial outcome. Be specific about the mechanism, not just the result. Include a realistic figure with context about where it comes from. 120-140 words.]</p>

<h3>[Benefit 2: Operational — specific efficiency, time, or performance improvement from {topic}]</h3>
<p>[Different metric from Benefit 1. Explain the mechanism. 120-140 words.]</p>

<h3>[Benefit 3: Strategic — competitive, reputational, or compliance advantage from {topic}]</h3>
<p>[Different from the first two. Long-term positioning value. 120-140 words.]</p>

<blockquote><strong>The compounding effect:</strong> [How these 3 benefits reinforce each other over time when {audience} invests properly in {topic}. 2-3 sentences.]</blockquote>

BANNED: Benefits that sound good but are impossible to verify. "Improve morale", "enhance reputation" without specifics. Every benefit needs a mechanism.
Output: raw HTML only.""",

"case_study": """\
Write the REAL WORLD CASE STUDY section for a premium guide on **{topic}** for **{audience}**.

This must read like a real case study — specific, credible, detailed. Not a vague story.

MANDATORY STRUCTURE:

<h3>Case Study: [Specific descriptive title that names the situation, not just "Case Study"]</h3>

<p><strong>The situation:</strong> [Organisation type, size/scale, location type, what they were trying to achieve with {topic}. Specific enough to feel real. 60-80 words.]</p>

<p><strong>The problem:</strong> [The exact challenge they faced with {topic}. What had already failed. What was at stake. Name the specific constraint or failure mode. 80-100 words.]</p>

<p><strong>The approach:</strong> [What they actually did — specific steps, tools, methods, decisions. No generics like "they implemented best practices". Name the actual things they did related to {topic}. 100-120 words.]</p>

<p><strong>The results:</strong> [At minimum 3 outcomes. Each must use a different metric. Numbers must feel realistic and earned, not round. E.g. "37% reduction" not "40% reduction". 80-100 words.]</p>

<blockquote><strong>The lesson for {audience}:</strong> [The single most transferable insight from this case — what it proves about {topic} that others should replicate. 40-60 words.]</blockquote>

BANNED: The word "implement", "leverage", "utilize". Vague outcomes like "significant improvement". Every result must have a number and a unit.
Output: raw HTML only.""",

"risk_management": """\
Write the RISK MANAGEMENT section for a premium guide on **{topic}** for **{audience}**.

These risks must be the ones that actually hurt people in {topic} — not obvious generic risks.

MANDATORY STRUCTURE:

<p>[Opener: why risk management in {topic} is different from general risk thinking — the specific nature of failure in this domain. 50-70 words.]</p>

<h3>[Risk 1: Technical/Execution — a specific failure mode in {topic} that catches experts off guard]</h3>
<p>[How it manifests, what triggers it, why even experienced {audience} miss it. 80-100 words.]</p>
<p><strong>How to prevent it:</strong> [Specific action, checklist, test, or process that neutralises this risk in {topic}. 60-80 words.]</p>

<h3>[Risk 2: Compliance/Legal — a specific regulatory or standards risk in {topic}]</h3>
<p>[What the rule requires, where people fall short, what the consequence is. 80-100 words.]</p>
<p><strong>How to prevent it:</strong> [Specific safeguard. 60-80 words.]</p>

<h3>[Risk 3: Commercial/Strategic — a risk that kills the business case for {topic}]</h3>
<p>[How this risk emerges, often late in the process, and why it is hard to see coming. 80-100 words.]</p>
<p><strong>How to prevent it:</strong> [Specific safeguard. 60-80 words.]</p>

<blockquote><strong>The risk most people skip:</strong> [Name the single most underestimated risk in {topic} and why it gets ignored. 2-3 sentences.]</blockquote>

BANNED: Generic risks like "budget overrun" or "timeline slippage" without specific causes tied to {topic}.
Output: raw HTML only.""",

"implementation_roadmap": """\
Write the IMPLEMENTATION ROADMAP section for a premium guide on **{topic}** for **{audience}**.

This is the section {audience} will screenshot and pin to their wall. Make it that useful.

MANDATORY STRUCTURE:

<p>[Opener: the most common sequencing mistake {audience} make when implementing {topic} — what they do first that they should do third. 50-70 words.]</p>

<h3>Phase 1: [Name specific to {topic}] — [Duration]</h3>
<p>[What happens, who does what, what decision or deliverable marks the END of this phase. 70-90 words.]</p>

<h3>Phase 2: [Name] — [Duration]</h3>
<p>[70-90 words. Different from Phase 1.]</p>

<h3>Phase 3: [Name] — [Duration]</h3>
<p>[70-90 words.]</p>

<h3>Phase 4: [Name] — [Duration]</h3>
<p>[70-90 words.]</p>

<h3>Phase 5: [Name] — [Duration]</h3>
<p>[70-90 words.]</p>

<h3>Phase 6: [Name] — [Duration]</h3>
<p>[70-90 words.]</p>

<blockquote><strong>The milestone that matters most:</strong> [Name the single phase transition in {topic} implementation where most projects either succeed or fail permanently — and what makes the difference.]</blockquote>

BANNED: Phases named "Planning", "Execution", "Review" — too generic. Each phase name must reflect something specific about how {topic} actually works.
Output: raw HTML only.""",

"future_trends": """\
Write the FUTURE TRENDS section for a premium guide on **{topic}** for **{audience}**.

These trends must be specific to {topic} — not generic "AI will change everything" statements.

MANDATORY STRUCTURE:

<p>[Opener: the single biggest shift happening in {topic} right now that most {audience} are underestimating. 50-70 words.]</p>

<h3>[Trend 1 — name it specifically, tied to {topic}]</h3>
<p>[What is driving this trend in {topic}. What it will change. When. What {audience} should do in the next 12 months to prepare. Include a specific market signal or timeline. 100-120 words.]</p>

<h3>[Trend 2 — different force in {topic}]</h3>
<p>[Same format. 100-120 words.]</p>

<h3>[Trend 3 — different force]</h3>
<p>[100-120 words.]</p>

<h3>[Trend 4 — different force]</h3>
<p>[100-120 words.]</p>

<blockquote><strong>The trend to act on now:</strong> [Which of the 4 trends has the shortest window before it becomes table stakes in {topic} — and what the cost of waiting is. 2-3 sentences.]</blockquote>

BANNED: Trends that are already mainstream. Trends not specific to {topic}. Generic "digital transformation" or "AI disruption" without specific connection to {topic}.
Output: raw HTML only.""",

"key_takeaways": """\
Write the KEY TAKEAWAYS section for a premium guide on **{topic}** for **{audience}**.

This is the last section before the CTA. It must crystallise everything and create momentum.

MANDATORY STRUCTURE:

<p>[Opener: a single sentence that frames what the reader now knows about {topic} that they didn't know at the start. 30-40 words.]</p>

<ul>
  <li><strong>[Takeaway 1 label — from the challenges section]:</strong> [The most important insight about what makes {topic} hard, in 40-60 words. Specific. Memorable.]</li>
  <li><strong>[Takeaway 2 label — from the strategies section]:</strong> [The most actionable thing to do about {topic}. 40-60 words.]</li>
  <li><strong>[Takeaway 3 label — from the risks section]:</strong> [The most important thing to avoid in {topic}. 40-60 words.]</li>
  <li><strong>[Takeaway 4 label — from the benefits section]:</strong> [The financial or strategic case for {topic} in one clear statement. 40-60 words.]</li>
  <li><strong>[Takeaway 5 label — from the trends section]:</strong> [What changes if {audience} waits 12 months to act on {topic}. 40-60 words.]</li>
</ul>

<blockquote><strong>The one thing:</strong> [If the reader only does one thing after reading this guide, what should it be? Make it concrete and specific to {topic}. 2-3 sentences.]</blockquote>

<p>[Closing transition — 1-2 sentences that naturally lead the reader to want to take the next step. Create gentle urgency without pressure. Specific to {topic}.]</p>

BANNED: Vague takeaways like "sustainable architecture is important". Every takeaway must contain a specific, actionable or protective insight.
Output: raw HTML only.""",

"call_to_action": """\
Write the CALL TO ACTION section for a premium guide on **{topic}** for **{audience}**.

This section converts readers into enquiries. It must feel helpful, not salesy.

MANDATORY STRUCTURE:

<h3>[Heading that speaks to where the reader is NOW after reading this guide about {topic}]</h3>
<p>[Acknowledge what they now understand about {topic} that makes the path forward clearer. Reference a specific insight from the guide. Then name the specific gap between knowing and doing that a consultation closes. 100-120 words.]</p>

<h3>What the First Conversation Looks Like</h3>
<p>[Describe the first meeting in concrete terms. What specific questions about {topic} get answered. What the reader walks away with — not a sales pitch, an actual deliverable or clarity. Why there is no risk to saying yes. 100-120 words.]</p>

<h3>Why Timing Matters for {topic}</h3>
<p>[One specific, real reason why acting on {topic} in the next 90 days is smarter than waiting — a market condition, upcoming deadline, cost trajectory, or competitive shift specific to {topic}. Not manufactured urgency. 70-90 words.]</p>

<blockquote><strong>The next step:</strong> [One clear, low-pressure action the reader can take right now. Specific. Simple. Not "contact us for more information".]</blockquote>

BANNED: "Contact us today!", "Don't miss out!", "Limited time offer", "Our team of experts". Write as a trusted adviser giving honest advice about the right next step for {topic}.
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
        api_key          = api_key or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        self.client      = Groq(api_key=api_key) if api_key else None
        self.model       = "llama-3.3-70b-versatile"
        self.temperature = 0.72
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
        Pass 1a — Title generation (1 small call, ~120 tokens)
        Pass 1b — One focused API call per section (11 calls × up to 4096 tokens)
                  GROQ_CALL_DELAY_SECONDS pause between calls to avoid rate-limit errors.
        Pass 2  — Assemble into return structure
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
            f"You are writing one section of a PREMIUM $49 downloadable lead magnet on '{topic}' for {audience}.\n\n"
            "ABSOLUTE RULES — violating any of these means the content is rejected:\n"
            "1. Raw HTML only. Zero markdown. Zero preamble ('Here is...', 'Sure!'). Zero sign-off.\n"
            f"2. Every sentence must be SPECIFIC to '{topic}' and '{audience}'. Zero generic business advice.\n"
            "3. ZERO repetition. Never repeat a phrase, stat, or idea from earlier in the same section.\n"
            "4. Stats ONLY if they have: a source name, a unit, and a sentence explaining what they mean.\n"
            "5. Every section must use at least 2 of these visual elements:\n"
            "   - <blockquote> for an insight, tip, or key takeaway\n"
            "   - <ul>/<li> for a practical list (not bullet-point padding)\n"
            "   - <strong> to highlight the single most important term per paragraph\n"
            "6. Sections must END with a complete thought. Never truncate mid-sentence.\n"
            "7. Minimum 350 words. Dense, expert-level prose. No padding.\n"
            "8. Write like a trusted adviser who has done this 100 times — confident, specific, direct."
        )

        sections_content: Dict[str, str] = {}

        for idx, (key, default_title, default_label, _, _) in enumerate(SECTIONS):
            # FIX 2 (rate limiting): pause between each Groq call.
            # Skip delay before the very first call; title call already ran.
            if idx > 0:
                logger.debug(f"  ⏳ Rate-limit pause ({GROQ_CALL_DELAY_SECONDS}s)…")
                time.sleep(GROQ_CALL_DELAY_SECONDS)

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

            def _call_groq(temp):
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user",   "content": user_msg},
                    ],
                    temperature=temp,
                    max_tokens=self.max_tokens,
                )
                raw = resp.choices[0].message.content.strip()
                raw = re.sub(r'^```html?\s*', '', raw, flags=re.IGNORECASE)
                raw = re.sub(r'\s*```\s*$', '', raw)
                raw = _sanitize_html(raw)
                if len(_html_to_text(raw)) < 50:
                    raise ValueError(f"Section too short: {len(_html_to_text(raw))} chars")
                return raw

            try:
                sections_content[key] = _call_groq(self.temperature)
                logger.info(f"  ✅ {key}: {len(sections_content[key])} chars")
            except Exception as e:
                logger.warning(f"  ⚠️  {key} failed: {e} — retrying after delay")
                time.sleep(GROQ_CALL_DELAY_SECONDS * 2)   # longer pause on error
                try:
                    sections_content[key] = _call_groq(min(self.temperature + 0.1, 0.9))
                    logger.info(f"  ✅ {key} (retry): {len(sections_content[key])} chars")
                except Exception as e2:
                    logger.error(f"  ❌ {key} retry failed: {e2}")
                    # FIX 5: Empty string so {{#if section_X_full_html}} evaluates
                    # falsy and the entire section div is omitted from the PDF,
                    # rather than rendering a placeholder-text page.
                    sections_content[key] = ""

        filled = sum(1 for k in SECTION_KEYS if len(sections_content.get(k, "")) > 100)
        logger.info(f"✅ Complete | {filled}/{len(SECTION_KEYS)} sections filled")

        return {
            "title":               title,
            "subtitle":            subtitle,
            "document_type":       doc_type,
            "document_type_label": type_label,
            "sections": {
                key: {"content": sections_content.get(key, ""), "title": dtitle}
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
            content  = sec_data.get("content", "") if isinstance(sec_data, dict) else str(sec_data)
            title    = (sec_data.get("title", "") if isinstance(sec_data, dict) else "") or default_title

            normalized[key] = _sanitize_html(str(content))
            normalized["framework"][key] = {"title": title or default_title, "kicker": default_label}

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
            "documentTypeLabel": doc_type_label,
            "mainTitle":         ai_content.get("title") or topic,
            "documentSubtitle":  subtitle,
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
            "termsParagraph4": f"{company_name} accepts no liability for errors, omissions, or outcomes arising from the use of this material.",
            "termsParagraph5": f"All recommendations should be validated by a qualified {signals.get('industry', topic)} professional before implementation.",
        }

        # Image slots — only set when a real URL exists.
        # Absent key → {{#if image_N_url}} is falsy → block is removed cleanly.
        for i in range(1, 7):
            url = str(firm_profile.get(f"image_{i}_url") or "").strip()
            if url:
                tvars[f"image_{i}_url"] = url

        # TOC — pre-built HTML injected as a single variable
        toc_parts = []
        for idx, (key, default_title, _, _, _) in enumerate(SECTIONS):
            fw    = ai_content.get("framework", {}).get(key, {})
            title = fw.get("title") or default_title
            page  = str(idx + 4).zfill(2)
            toc_parts.append(
                f'<div class="toc-item">'
                f'<span class="toc-num">{str(idx + 1).zfill(2)}</span>'
                f'<span class="toc-label">{title}</span>'
                f'<span class="toc-pg">{page}</span>'
                f'</div>'
            )
        tvars["toc_sections_html"] = "\n".join(toc_parts)
        tvars["toc_html"]          = tvars["toc_sections_html"]

        # Per-section vars
        for idx, (key, default_title, default_label, _, _) in enumerate(SECTIONS):
            fw      = ai_content.get("framework", {}).get(key, {})
            title   = fw.get("title") or default_title
            content = ai_content.get(key, "")
            s_idx   = idx + 1

            tvars[f"customTitle{s_idx}"]          = title
            tvars[f"section_{key}_full_html"]      = content
            tvars[f"section_{key}_id"]             = f"section-{key}"
            tvars[f"section_{key}_title"]          = title
            tvars[f"section_{key}_kicker"]         = default_label
            tvars[f"section_{key}_intro"]          = self._extract_intro_text(content)
            tvars[f"section_{key}_support"]        = self._extract_support_text(content)
            sv, sl = self._extract_stat(content)
            tvars[f"section_{key}_stat_val"]       = sv
            tvars[f"section_{key}_stat_lbl"]       = sl
            tvars[f"section_{key}_bullets_html"]   = self._extract_bullets_html(content)

        for n in range(2, 16):
            tvars[f"pageNumber{n}"]       = str(n).zfill(2)
            tvars[f"pageNumberHeader{n}"] = str(n).zfill(2)

        return tvars

    # ──────────────────────────────────────────────────────────────────────
    # TEMPLATE RENDERING (call this before PDF generation)
    # ──────────────────────────────────────────────────────────────────────

    def render_html(self, template: str, vars: Dict[str, Any]) -> str:
        """
        Render the HTML template — resolves all {{#if}} blocks and {{VAR}}
        substitutions BEFORE the HTML is passed to PrinceXML / WeasyPrint.

        This MUST be called. Skipping it is what caused raw {{#if image_1_url}}
        and stray {{/if}} pages to appear in the PDF.

        Example usage:
            template_str  = open("Template.html").read()
            ai_content    = client.normalize_ai_output(client.generate_lead_magnet_json(...))
            template_vars = client.map_to_template_vars(ai_content, firm_profile, signals)
            rendered_html = client.render_html(template_str, template_vars)
            # → pass rendered_html to prince / weasyprint
        """
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
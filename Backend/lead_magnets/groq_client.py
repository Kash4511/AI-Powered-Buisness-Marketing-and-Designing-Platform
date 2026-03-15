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
# SECTION DEFINITIONS — 12 content sections used by the HTML template.
# These NEVER change — the template {{section_*_html}} vars depend on them.
# What changes per doc_type is the PROMPT BRIEF sent to the AI.
# ─────────────────────────────────────────────────────────────────────────────
SECTIONS = [
    (
        "executive_summary",
        "Introduction",
        "OVERVIEW",
        "text-only",
        (
            "Write a friendly and engaging Introduction for a guide on {topic} aimed at {audience}.\n"
            "The tone should be like an experienced architect giving helpful advice to a client.\n"
            "RULES:\n"
            "  • Explain the topic in simple terms and why it matters today.\n"
            "  • Avoid technical jargon or academic writing.\n"
            "  • Use simple explanations and relatable language.\n"
            "STRUCTURE:\n"
            "<p>A warm opening that defines {topic} simply and why it's a great choice for {audience}.</p>\n"
            "<h3>Why This Matters Now</h3>\n"
            "<p>Explain the benefits (comfort, cost savings, health) in plain English.</p>\n"
            "<h3>The Goal of This Guide</h3>\n"
            "<p>A brief encouraging statement on how this guide helps them make better decisions.</p>\n"
            "TARGET: 300–350 words."
        )
    ),
    (
        "key_challenges",
        "Common Challenges",
        "CHALLENGES",
        "image-right",
        (
            "Describe 4 real problems clients face when starting a project related to {topic}.\n"
            "RULES:\n"
            "  • Use simple, non-technical language.\n"
            "  • Focus on the client's perspective and feelings.\n"
            "STRUCTURE — for each challenge:\n"
            "<h3>[Simple Challenge Name]</h3>\n"
            "<p>Explain the problem in 2-3 sentences. Why does it happen?</p>\n"
            "<p><strong>Why it's frustrating:</strong> The real-world impact on their time or budget.</p>\n"
            "<p><strong>How we help:</strong> A simple way an architect resolves this.</p>\n"
            "TARGET: 300–350 words."
        )
    ),
    (
        "strategic_framework",
        "Key Principles",
        "PRINCIPLES",
        "image-left",
        (
            "Explain the core ideas of {topic} that {audience} should understand.\n"
            "STRUCTURE:\n"
            "<p>Introduction to 3 main 'pillars' of good design for {topic}.</p>\n"
            "<h3>Principle 1: [Simple Name]</h3>\n"
            "<p>A clear, plain-English explanation with a relatable example.</p>\n"
            "<h3>Principle 2: [Simple Name]</h3>\n"
            "<p>A clear, plain-English explanation with a relatable example.</p>\n"
            "<h3>Principle 3: [Simple Name]</h3>\n"
            "<p>A clear, plain-English explanation with a relatable example.</p>\n"
            "TARGET: 300–350 words."
        )
    ),
    (
        "implementation_strategy",
        "Practical Strategies",
        "STRATEGIES",
        "text-only",
        (
            "Provide 3 actionable strategies {audience} can follow for their {topic} project.\n"
            "STRUCTURE:\n"
            "<h3>Strategy 1: [Actionable Name]</h3>\n"
            "<p>What it is and how it works.</p>\n"
            "<ul><li><strong>Why it matters:</strong> Benefit to the client.</li>\n"
            "<li><strong>Example:</strong> A simple real-world scenario.</li></ul>\n"
            "Repeat for Strategy 2 and 3.\n"
            "TARGET: 300–350 words."
        )
    ),
    (
        "risk_management",
        "Managing Your Project Risks",
        "RISK",
        "image-above",
        (
            "Explain how to avoid common risks in {topic} projects in simple language.\n"
            "STRUCTURE:\n"
            "<h3>[Risk Name]</h3>\n"
            "<p>What the risk is and how it usually starts.</p>\n"
            "<p><strong>Smart Solution:</strong> Practical advice on how to prevent it early.</p>\n"
            "TARGET: 300–350 words."
        )
    ),
    (
        "best_practices",
        "Best Practices for Success",
        "TIPS",
        "text-only",
        (
            "Outline professional tips for {audience} to ensure their project is a success.\n"
            "STRUCTURE:\n"
            "<h3>[Tip Name]</h3>\n"
            "<p>The advice explained simply.</p>\n"
            "<p><strong>The Result:</strong> What they gain by following this tip.</p>\n"
            "TARGET: 300–350 words."
        )
    ),
    (
        "key_statistics",
        "Facts and Figures",
        "DATA",
        "text-only",
        (
            "Provide interesting facts or simple statistics about {topic}.\n"
            "STRUCTURE:\n"
            "<h3>Did You Know?</h3>\n"
            "<p>3-4 interesting facts presented simply.</p>\n"
            "<ul><li><strong>[Fact Label]:</strong> [The fact/stat explained]</li></ul>\n"
            "TARGET: 250–300 words."
        )
    ),
    (
        "process_steps",
        "Implementation Roadmap",
        "ROADMAP",
        "text-only",
        (
            "Explain step-by-step how someone can apply these ideas when starting a project.\n"
            "STRUCTURE:\n"
            "<h3>Step 1: [Simple Phase Name]</h3>\n"
            "<p>What happens in this stage and what the client needs to do.</p>\n"
            "Repeat for 5 steps.\n"
            "TARGET: 300–350 words."
        )
    ),
    (
        "comparison_table",
        "Traditional vs. Smart Design",
        "COMPARISON",
        "text-only",
        (
            "Compare traditional building methods with {topic} approaches simply.\n"
            "STRUCTURE:\n"
            "<h3>[Comparison Point]</h3>\n"
            "<p>Contrast the two approaches simply.</p>\n"
            "TARGET: 300–350 words."
        )
    ),
    (
        "key_takeaways",
        "Key Lessons",
        "SUMMARY",
        "text-only",
        (
            "Summarize the most important lessons from this guide in simple bullet points.\n"
            "STRUCTURE:\n"
            "<h3>Important Takeaways</h3>\n"
            "<ul><li>[Takeaway 1]</li><li>[Takeaway 2]</li><li>[Takeaway 3]</li><li>[Takeaway 4]</li></ul>\n"
            "TARGET: 250–300 words."
        )
    ),
    (
        "case_study",
        "Real-World Example",
        "CASE STUDY",
        "text-only",
        (
            "Create a short real-world style example that demonstrates success.\n"
            "STRUCTURE:\n"
            "<h3>Example Project: [Project Type]</h3>\n"
            "<p><strong>Challenge:</strong> Explain the problem in 2-3 sentences.</p>\n"
            "<p><strong>Solution:</strong> Explain the strategies used.</p>\n"
            "<p><strong>Results:</strong> Explain the benefits achieved.</p>\n"
            "TARGET: 300–350 words."
        )
    ),
    (
        "conclusion",
        "Ready to Start Your Project?",
        "NEXT STEPS",
        "text-only",
        (
            "Create a final section to convert readers into potential clients.\n"
            "TONE: Friendly and professional.\n"
            "STRUCTURE:\n"
            "<h3>Ready to Start Your Project?</h3>\n"
            "<p>Encouraging advice and a specific invitation to consult.</p>\n"
            "TARGET: 250–300 words."
        )
    ),
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
    # lowercase / underscore variants
    "guide":                  "guide",
    "strategic_guide":        "guide",
    "case_study":             "case_study",
    "checklist":              "checklist",
    "roi_calculator":         "roi_calculator",
    "trends_report":          "trends_report",
    "design_portfolio":       "design_portfolio",
    "client_onboarding":      "client_onboarding",
    "client_onboarding_flow": "client_onboarding",
    "onboarding_flow":        "client_onboarding",
    "custom":                 "custom",
    # Human-readable (Title Case) variants — what the frontend actually sends
    "Guide":                  "guide",
    "Strategic Guide":        "guide",
    "Case Study":             "case_study",
    "Checklist":              "checklist",
    "ROI Calculator":         "roi_calculator",
    "Trends Report":          "trends_report",
    "Design Portfolio":       "design_portfolio",
    "Client Onboarding Flow": "client_onboarding",
    "Client Onboarding":      "client_onboarding",
    "Custom":                 "custom",
}

ALLOWED_TAGS = {"p", "strong", "em", "h3", "h4", "ul", "ol", "li", "br", "blockquote", "footer"}

# ─────────────────────────────────────────────────────────────────────────────
# FILLER DETECTION
# ─────────────────────────────────────────────────────────────────────────────
_FILLER_PATTERNS = [
    r"this (section|guide|document|report|checklist|article) (provides?|offers?|explores?|covers?|aims? to|is designed to)",
    r"in (today's|the current|this) (fast[- ]paced|rapidly changing|evolving|dynamic|competitive|modern)",
    r"it is (important|crucial|essential|critical|vital) (to note|to understand|that|to consider)",
    r"(as we|let us|let's|we will) (explore|delve|dive|look at|examine|discuss|uncover)",
    r"(understanding|navigating) the (complexities|nuances|intricacies|challenges) of",
    r"(the following|below) (section|content|information|steps|points) (will|provides?|outlines?|describes?)",
    r"in conclusion,? (this|it|we|as shown)",
    r"(to summarize|in summary|to recap|overall),",
    r"this comprehensive (guide|report|document|analysis)",
    r"(by the end of this|after reading this|now that you've read)",
    r"one of the most (significant|important|notable) (aspects|factors|elements)",
    r"it's worth (noting|mentioning|considering) that",
    r"furthermore,? (the|this|we)",
    r"additionally,? (the|this|we)",
    r"moreover,? (the|this|we)",
    r"consequently,? (the|this|we)",
    r"as a result,? (the|this|we)",
    r"first and foremost,?",
    r"lastly,? (the|this|we)",
    r"to put it simply,?",
    r"in other words,?",
]
_FILLER_RE = re.compile("|".join(_FILLER_PATTERNS), re.IGNORECASE)


def _strip_filler(html: str) -> str:
    if not html:
        return html
    # Split by sentences (handling basic punctuation)
    sentences = re.split(r'(?<=[.!?])\s+', html)
    cleaned = []
    for s in sentences:
        # If the sentence starts with a filler pattern, skip it
        if _FILLER_RE.match(s.strip()):
            logger.debug(f"Stripped filler sentence: {s[:60]}...")
            continue
        cleaned.append(s)
    return " ".join(cleaned)


def _deduplicate_content(html: str) -> str:
    if not html:
        return html
    seen = set()
    result = []
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


# ─────────────────────────────────────────────────────────────────────────────
# MASTER PROMPT — type-aware format rules injected per doc_type
# ─────────────────────────────────────────────────────────────────────────────
MASTER_PROMPT_TEMPLATE = """
You are a senior architectural consultant and high-end marketing strategist.
Your task is to generate a SUBSTANTIAL, HIGH-VALUE lead magnet that sounds like it was written by a human expert with 20+ years of experience.

CRITICAL DIRECTIVES:
1. NO AI FILLER: Eliminate all meta-talk (e.g., "In this section...", "This guide explores..."). Start every section with direct, impactful content.
2. HYPER-SPECIFICITY: Replace generic advice with precise, actionable insights. Use real-world analogies, specific architectural standards (e.g., Passive House, LEED, local zoning terms), and concrete metrics.
3. PERSONALIZATION: Weave the Topic, Audience, Pain Points, Psychographics, and Firm USP into every paragraph. The content must feel bespoke to this specific firm and their ideal client.
4. NO REPETITION: Ensure each section provides unique value. Do not repeat the same points across different headers.
5. TECHNICAL DEPTH: Provide "insider" knowledge that a client couldn't find with a simple Google search.

CONTENT DEPTH REQUIREMENTS:
- The guide must contain substantial content.
- Rules:
  • Each major section must contain 3–5 paragraphs.
  • Each paragraph should be 80–120 words.
  • Include bullet lists where helpful.
  • Provide examples or explanations when introducing ideas.
  • Avoid one-line sections or short filler text.
  • Never generate extremely short sections. If a section contains fewer than 2 paragraphs, expand it with additional explanations or examples.
- Minimum structure for each section:
  Section Title
  Paragraph explaining the topic.
  Paragraph explaining why it matters.
  Bullet list of practical considerations.
  Optional short example.
- Ensure the final guide would fill approximately 8–10 PDF pages when rendered.

IMAGE PLACEMENT RULES:
- Images must not appear randomly inside text.
- Images should only appear:
  • After section headers
  • Between paragraphs
  • Never inside bullet lists
  • Never mid-sentence
- Use this format for images:
  [IMAGE]
  Type: illustration / diagram / architecture / sustainability
  Description: short description
  Placement: after section header
  [/IMAGE]
- Example:
  ## Sustainable Building Orientation
  [IMAGE]
  Type: diagram
  Description: building orientation optimizing sunlight and ventilation
  Placement: after section header
  [/IMAGE]
  Paragraph text begins here.

IMAGE DISTRIBUTION:
- Include 5–7 images across the entire guide.
- Suggested placement:
  • Cover page hero image
  • Introduction illustration
  • 1 image every 1–2 sections
  • Final infographic or summary diagram
- Images should represent: sustainable buildings, green architecture concepts, eco materials, architectural diagrams, energy systems.
- Avoid generic stock imagery. Prefer diagrams or architectural visuals.

INPUT DATA:
Topic: {topic}
Lead Magnet Type: {lead_magnet_type}
Audience: {audience}
Pain Points: {pain_points}
Psychographics: {psychographics}
Firm USP: {firm_usp}

=============================================
FORMAT RULES FOR "{lead_magnet_type}":
{format_specific_rules}
=============================================

WRITING RULES:
- Tone: Authoritative, advisory, and sophisticated.
- Formatting: Use <h3> for sub-headings, <p> for paragraphs, <strong> for emphasis, <ul><li> for lists.
- Markdown: Output MUST be structured with Markdown headers:
  # [Vibrant, Non-Generic Title]
  ## [Section Name]
  [Section Content using raw HTML tags]

Do NOT include any introductory or concluding remarks about the task. Only output the lead magnet content.
"""

FORMAT_RULES = {
    "guide": """
Structure (use these EXACT ## header names):
## Introduction
(Hook the reader immediately. Define the topic through the lens of the Firm's USP.)
## Common Challenges
(Detail 4 sophisticated challenges. Focus on hidden costs, regulatory traps, and aesthetic vs. functional trade-offs.)
## Key Principles
(Provide 3-4 "golden rules" of design for this topic. Use specific analogies.)
## Practical Strategies
(3 high-impact strategies. Include "how-to" steps and expected outcomes.)
## Managing Risks
(Identify 3 non-obvious risks—e.g., liability, long-term maintenance, or contractor shortcuts—and provide professional mitigations.)
## Best Practices
(Advanced "insider" tips that demonstrate the firm's superior expertise.)
## Facts and Figures
(Include specific, verifiable metrics related to ROI, sustainability, or property value.)
## Implementation Roadmap
(A 5-phase strategic timeline from vision to handover.)
## Traditional vs Modern
(A sharp comparison of outdated methods vs. the firm's innovative approach.)
## Key Lessons
(Distill the most critical strategic takeaways into 4 punchy bullets.)
## Real World Example
(A detailed client success story: Challenge, the firm's Unique Mechanism, and the Transformation.)
## Ready to Start
(A sophisticated call to action that positions the firm as the only logical partner.)
""",
    "checklist": """
Structure (use these EXACT ## header names):
## Introduction
## Planning Checklist
## Design Checklist
## Construction Checklist
## Quality Review Checklist
## Key Principles
## Managing Risks
## Best Practices
## Facts and Figures
## Key Lessons
## Real World Example
## Ready to Start

Requirements:
- For each checklist section, provide high-value, non-obvious tasks.
- Format:
<h3>[Phase Name]</h3>
<ul>
<li>☐ <strong>[Task Name]:</strong> [Detailed explanation of why this matters and how to execute it.]</li>
</ul>
""",
    "case_study": """
Structure (use these EXACT ## header names):
## Introduction
## Project Overview
## Key Challenges
## Our Approach
## Implementation Steps
## Managing Risks
## Results Achieved
## Facts and Figures
## Key Lessons
## Real World Example
## Additional Insights
## Ready to Start

Requirements:
- Write this as a deep-dive narrative.
- Focus on the "Unique Mechanism" used to solve complex problems.
- Use <h3> for sub-phases of the project.
""",
    "roi_calculator": """
Structure (use these EXACT ## header names):
## Introduction
## Why ROI Matters
## Cost Factors
## ROI Breakdown
## Scenario Example One
## Scenario Example Two
## Managing Risks
## Best Practices
## Facts and Figures
## Key Lessons
## Real World Example
## Ready to Start

Requirements:
- For ROI Breakdown, provide a technical breakdown of costs vs. long-term savings.
- Use specific scenarios (e.g., "A 3,000 sq ft renovation") to ground the data.
""",
    "trends_report": """
Structure (use these EXACT ## header names):
## Introduction
## Major Trend One
## Major Trend Two
## Major Trend Three
## Market Drivers
## Opportunities for Firms
## Managing Risks
## Best Practices
## Facts and Figures
## Key Lessons
## Real World Example
## Ready to Start

Requirements:
- Provide forward-looking intelligence.
- Explain *why* these trends are happening and how to capitalize on them.
""",
    "client_onboarding": """
Structure (use these EXACT ## header names):
## Introduction
## Initial Consultation
## Project Discovery
## Design Planning
## Approval and Permitting
## Construction Coordination
## Managing Risks
## Best Practices
## Facts and Figures
## Key Lessons
## Real World Example
## Ready to Start

Requirements:
- Map out a premium, high-touch experience.
- Focus on transparency, communication, and expectation management.
""",
    "design_portfolio": """
Structure (use these EXACT ## header names):
## Introduction
## About Our Firm
## Project Highlight One
## Project Highlight Two
## Design Philosophy
## Managing Risks
## Best Practices
## Facts and Figures
## Key Lessons
## Real World Example
## Our Process
## Ready to Start

Requirements:
- Focus on the "Art and Science" of the firm's work.
- Use descriptive language that evokes quality and craftsmanship.
""",
    "custom": """
Structure (use these EXACT ## header names):
## Introduction
## Key Insights
## Core Framework
## Practical Strategies
## Managing Risks
## Best Practices
## Facts and Figures
## Implementation Steps
## Comparison Analysis
## Key Lessons
## Real World Example
## Ready to Start
"""
}

# ─────────────────────────────────────────────────────────────────────────────
# TYPE-AWARE SECTION MAPPING
# Maps any AI-generated ## header → one of the 12 SECTIONS keys.
# Each doc_type gets its own priority mapping so nothing falls through.
# ─────────────────────────────────────────────────────────────────────────────
_SECTION_MAPS: Dict[str, Dict[str, str]] = {
    "guide": {
        "introduction":          "executive_summary",
        "overview":              "executive_summary",
        "executive_summary":     "executive_summary",
        "common_challenges":     "key_challenges",
        "challenges":            "key_challenges",
        "key_principles":        "strategic_framework",
        "principles":            "strategic_framework",
        "practical_strategies":  "implementation_strategy",
        "strategies":            "implementation_strategy",
        "managing_risks":        "risk_management",
        "risk_management":       "risk_management",
        "risks":                 "risk_management",
        "best_practices":        "best_practices",
        "facts_and_figures":     "key_statistics",
        "facts":                 "key_statistics",
        "statistics":            "key_statistics",
        "implementation_roadmap":"process_steps",
        "roadmap":               "process_steps",
        "steps":                 "process_steps",
        "traditional_vs_modern": "comparison_table",
        "comparison":            "comparison_table",
        "key_lessons":           "key_takeaways",
        "key_takeaways":         "key_takeaways",
        "takeaways":             "key_takeaways",
        "lessons":               "key_takeaways",
        "real_world_example":    "case_study",
        "case_study":            "case_study",
        "example":               "case_study",
        "ready_to_start":        "conclusion",
        "conclusion":            "conclusion",
        "next_steps":            "conclusion",
        "cta":                   "conclusion",
    },
    "checklist": {
        "introduction":          "executive_summary",
        "planning_checklist":    "key_challenges",
        "planning":              "key_challenges",
        "design_checklist":      "strategic_framework",
        "design":                "strategic_framework",
        "construction_checklist":"implementation_strategy",
        "construction":          "implementation_strategy",
        "quality_review_checklist": "risk_management",
        "quality_review":        "risk_management",
        "key_principles":        "best_practices",
        "principles":            "best_practices",
        "managing_risks":        "risk_management",
        "best_practices":        "best_practices",
        "facts_and_figures":     "key_statistics",
        "facts":                 "key_statistics",
        "key_lessons":           "key_takeaways",
        "lessons":               "key_takeaways",
        "real_world_example":    "case_study",
        "example":               "case_study",
        "ready_to_start":        "conclusion",
        "conclusion":            "conclusion",
        # fill remaining slots
        "implementation_roadmap":"process_steps",
        "traditional_vs_modern": "comparison_table",
    },
    "case_study": {
        "introduction":          "executive_summary",
        "project_overview":      "key_challenges",
        "overview":              "executive_summary",
        "key_challenges":        "key_challenges",
        "challenges":            "key_challenges",
        "our_approach":          "strategic_framework",
        "approach":              "strategic_framework",
        "implementation_steps":  "process_steps",
        "implementation":        "process_steps",
        "managing_risks":        "risk_management",
        "risks":                 "risk_management",
        "results_achieved":      "key_statistics",
        "results":               "key_statistics",
        "facts_and_figures":     "key_statistics",
        "key_lessons":           "key_takeaways",
        "lessons":               "key_takeaways",
        "real_world_example":    "case_study",
        "additional_insights":   "best_practices",
        "ready_to_start":        "conclusion",
        "conclusion":            "conclusion",
        "best_practices":        "best_practices",
        "traditional_vs_modern": "comparison_table",
        "strategies":            "implementation_strategy",
    },
    "roi_calculator": {
        "introduction":          "executive_summary",
        "why_roi_matters":       "key_challenges",
        "cost_factors":          "strategic_framework",
        "roi_breakdown":         "implementation_strategy",
        "scenario_example_one":  "process_steps",
        "scenario_example_two":  "comparison_table",
        "managing_risks":        "risk_management",
        "best_practices":        "best_practices",
        "facts_and_figures":     "key_statistics",
        "key_lessons":           "key_takeaways",
        "real_world_example":    "case_study",
        "ready_to_start":        "conclusion",
        "conclusion":            "conclusion",
    },
    "trends_report": {
        "introduction":          "executive_summary",
        "major_trend_one":       "key_challenges",
        "major_trend_two":       "strategic_framework",
        "major_trend_three":     "implementation_strategy",
        "market_drivers":        "risk_management",
        "opportunities_for_firms":"best_practices",
        "managing_risks":        "risk_management",
        "best_practices":        "best_practices",
        "facts_and_figures":     "key_statistics",
        "key_lessons":           "key_takeaways",
        "real_world_example":    "case_study",
        "ready_to_start":        "conclusion",
        "conclusion":            "conclusion",
        "traditional_vs_modern": "comparison_table",
        "roadmap":               "process_steps",
    },
    "client_onboarding": {
        "introduction":          "executive_summary",
        "initial_consultation":  "key_challenges",
        "project_discovery":     "strategic_framework",
        "design_planning":       "implementation_strategy",
        "approval_and_permitting":"process_steps",
        "construction_coordination":"comparison_table",
        "managing_risks":        "risk_management",
        "best_practices":        "best_practices",
        "facts_and_figures":     "key_statistics",
        "key_lessons":           "key_takeaways",
        "real_world_example":    "case_study",
        "ready_to_start":        "conclusion",
        "conclusion":            "conclusion",
    },
    "design_portfolio": {
        "introduction":          "executive_summary",
        "about_our_firm":        "key_challenges",
        "project_highlight_one": "strategic_framework",
        "project_highlight_two": "implementation_strategy",
        "design_philosophy":     "risk_management",
        "managing_risks":        "risk_management",
        "best_practices":        "best_practices",
        "facts_and_figures":     "key_statistics",
        "key_lessons":           "key_takeaways",
        "real_world_example":    "case_study",
        "our_process":           "process_steps",
        "ready_to_start":        "conclusion",
        "conclusion":            "conclusion",
        "traditional_vs_modern": "comparison_table",
    },
    "custom": {
        "introduction":          "executive_summary",
        "key_insights":          "key_challenges",
        "core_framework":        "strategic_framework",
        "practical_strategies":  "implementation_strategy",
        "managing_risks":        "risk_management",
        "best_practices":        "best_practices",
        "facts_and_figures":     "key_statistics",
        "implementation_steps":  "process_steps",
        "comparison_analysis":   "comparison_table",
        "key_lessons":           "key_takeaways",
        "real_world_example":    "case_study",
        "ready_to_start":        "conclusion",
        "conclusion":            "conclusion",
    },
}

# Fallback universal mapping (used when doc_type not found or slug not in type map)
_UNIVERSAL_SLUG_MAP = {
    "introduction":          "executive_summary",
    "overview":              "executive_summary",
    "summary":               "executive_summary",
    "challenges":            "key_challenges",
    "problems":              "key_challenges",
    "framework":             "strategic_framework",
    "principles":            "strategic_framework",
    "strategies":            "implementation_strategy",
    "strategy":              "implementation_strategy",
    "risks":                 "risk_management",
    "risk":                  "risk_management",
    "tips":                  "best_practices",
    "practices":             "best_practices",
    "facts":                 "key_statistics",
    "statistics":            "key_statistics",
    "data":                  "key_statistics",
    "figures":               "key_statistics",
    "steps":                 "process_steps",
    "roadmap":               "process_steps",
    "phases":                "process_steps",
    "process":               "process_steps",
    "comparison":            "comparison_table",
    "vs":                    "comparison_table",
    "versus":                "comparison_table",
    "takeaways":             "key_takeaways",
    "lessons":               "key_takeaways",
    "insights":              "key_takeaways",
    "case":                  "case_study",
    "example":               "case_study",
    "project":               "case_study",
    "results":               "case_study",
    "conclusion":            "conclusion",
    "next":                  "conclusion",
    "start":                 "conclusion",
    "cta":                   "conclusion",
    "contact":               "conclusion",
}

# ─────────────────────────────────────────────────────────────────────────────
# SLOT ORDER — defines which SECTIONS key gets priority when assigning content.
# When two parsed sections map to the same key, first one wins.
# ─────────────────────────────────────────────────────────────────────────────
SECTION_KEYS = [s[0] for s in SECTIONS]


class GroqClient:
    SECTIONS = SECTIONS
    DOC_TYPE_LABELS = DOC_TYPE_LABELS
    _TYPE_MAP = _TYPE_MAP
    SECTION_LAYOUT = {key: layout for key, _, _, layout, _ in SECTIONS}

    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        # For testing purposes, we allow initializing without a key if we only use mapping methods
        self.client      = Groq(api_key=api_key) if api_key else None
        self.model       = "llama-3.3-70b-versatile"
        self.temperature = 0.55
        self.max_tokens  = 4096
        self._analysis   = None
        self._framework  = None

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, Any]:
        raw_type = str(
            user_answers.get("document_type")
            or user_answers.get("lead_magnet_type")
            or "guide"
        ).strip()

        # Try exact match first (handles "Checklist", "ROI Calculator" etc.)
        doc_type = _TYPE_MAP.get(raw_type)
        if not doc_type:
            # Try normalized (lowercase + underscores)
            normalized = raw_type.lower().replace("-", "_").replace(" ", "_")
            doc_type = _TYPE_MAP.get(normalized, "guide")

        logger.info(f"🗂️  doc_type resolved: '{raw_type}' → '{doc_type}'")

        pain_points = user_answers.get("pain_points", [])
        audience    = user_answers.get("target_audience", "Stakeholders")

        return {
            "topic":           user_answers.get("main_topic", "Strategic Design"),
            "audience":        ", ".join(audience) if isinstance(audience, list) else str(audience),
            "pain_points":     ", ".join(pain_points) if isinstance(pain_points, list) else str(pain_points),
            "psychographics":  str(user_answers.get("psychographics", "")).strip(),
            "firm_usp":        str(user_answers.get("firm_usp", "")).strip(),
            "desired_outcome": user_answers.get("desired_outcome", ""),
            "cta":             user_answers.get("call_to_action", ""),
            "special":         user_answers.get("special_requests", ""),
            "tone":            user_answers.get("tone", "Professional and Friendly"),
            "industry":        user_answers.get("industry", "Architecture and Design"),
            "document_type":   doc_type,
        }

    def generate_lead_magnet_json(self, signals: Dict[str, Any], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        doc_type   = signals.get("document_type", "guide")
        type_label = DOC_TYPE_LABELS.get(doc_type) or DOC_TYPE_LABELS["guide"]
        logger.info(f"🚀 Unified Generation | type={doc_type} | label={type_label} | topic={signals['topic']}")

        format_rules = FORMAT_RULES.get(doc_type, FORMAT_RULES["custom"])
        prompt = MASTER_PROMPT_TEMPLATE.format(
            topic                 = signals["topic"],
            lead_magnet_type      = type_label,
            audience              = signals["audience"],
            pain_points           = signals["pain_points"],
            psychographics        = signals.get("psychographics", "None"),
            firm_usp              = signals.get("firm_usp", "None"),
            format_specific_rules = format_rules,
        )

        try:
            response = self.client.chat.completions.create(
                model       = self.model,
                messages    = [
                    {"role": "system", "content": "You are a professional marketing copywriter and strategist specialising in architecture firms."},
                    {"role": "user",   "content": prompt},
                ],
                temperature = self.temperature,
                max_tokens  = self.max_tokens,
            )
            raw_content = response.choices[0].message.content
            logger.info(f"✅ AI response length: {len(raw_content)} chars")
        except Exception as e:
            logger.error(f"Unified AI Call Failed: {e}")
            raise RuntimeError(f"AI Generation Error: {e}")

        parsed = self._parse_unified_content(raw_content, doc_type)
        logger.info(f"📋 Parsed sections: {list(parsed.get('sections', {}).keys())}")

        return {
            "title":               parsed.get("title", signals["topic"]),
            "subtitle":            parsed.get("subtitle", type_label),
            "document_type":       doc_type,
            "document_type_label": type_label,
            "sections":            parsed.get("sections", {}),
            "images":              parsed.get("images", []),
            "raw_output":          raw_content,
        }

    def _parse_unified_content(self, text: str, doc_type: str) -> Dict[str, Any]:
        """
        Splits unified Markdown response into structured sections,
        then maps them to SECTIONS keys using type-aware mapping.
        Also extracts [IMAGE] blocks.
        """
        parsed = {"title": "", "subtitle": "", "sections": {}, "images": []}

        # 1. Extract [IMAGE] blocks before splitting sections
        image_blocks = re.findall(r'\[IMAGE\](.*?)\[/IMAGE\]', text, re.S)
        for block in image_blocks:
            img_data = {}
            for line in block.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    img_data[k.strip().lower()] = v.strip()
            if img_data:
                parsed["images"].append(img_data)

        # Remove image blocks from text to avoid them being treated as content
        clean_text = re.sub(r'\[IMAGE\].*?\[/IMAGE\]', '', text, flags=re.S)

        # 2. Extract Main Title (# Header)
        title_match = re.search(r'^#\s*(.+)$', clean_text, re.MULTILINE)
        if title_match:
            full_title = title_match.group(1).strip()
            if ":" in full_title:
                parts = full_title.split(":", 1)
                parsed["title"]    = parts[0].strip()
                parsed["subtitle"] = parts[1].strip()
            else:
                parsed["title"] = full_title

        # 3. Split by ## headers
        sections_raw = re.split(r'^##\s*(?:\d+\.?\s*)?(.+)$', clean_text, flags=re.MULTILINE)

        # Get the type-specific mapping + universal fallback
        type_map = _SECTION_MAPS.get(doc_type, _SECTION_MAPS.get("guide", {}))

        # Track which SECTIONS keys have been filled (first match wins)
        filled: Dict[str, str]  = {}  # section_key → content
        filled_titles: Dict[str, str] = {}

        for i in range(1, len(sections_raw) - 1, 2):
            raw_header = sections_raw[i].strip()
            content    = sections_raw[i + 1].strip() if i + 1 < len(sections_raw) else ""
            if not content:
                continue

            # Build slug for matching
            header_slug = (
                raw_header.lower()
                .replace(" ", "_")
                .replace("&", "and")
                .replace("-", "_")
                .replace(":", "")
                .replace("'", "")
            )

            # 1. Try exact match in type_map
            section_key = type_map.get(header_slug)

            # 2. Try substring match in type_map
            if not section_key:
                for map_key, map_val in type_map.items():
                    if map_key in header_slug or header_slug in map_key:
                        section_key = map_val
                        break

            # 3. Try universal fallback map
            if not section_key:
                for slug_part, fallback_key in _UNIVERSAL_SLUG_MAP.items():
                    if slug_part in header_slug:
                        section_key = fallback_key
                        break

            # 4. Last resort: assign to the next unfilled SECTIONS slot
            if not section_key:
                for key in SECTION_KEYS:
                    if key not in filled:
                        section_key = key
                        logger.debug(f"⚠️  Unmapped header '{raw_header}' → fallback slot '{key}'")
                        break

            if section_key and section_key not in filled:
                filled[section_key]        = content
                filled_titles[section_key] = raw_header

        # Build final sections dict with proper structure
        for key in SECTION_KEYS:
            content = filled.get(key, "")
            title   = filled_titles.get(key, "")
            parsed["sections"][key] = {
                "content": content,
                "title":   title,
            }

        mapped_count = sum(1 for k in SECTION_KEYS if filled.get(k))
        logger.info(f"📊 Section mapping: {mapped_count}/{len(SECTION_KEYS)} slots filled for type='{doc_type}'")
        if mapped_count < len(SECTION_KEYS) // 2:
            logger.warning(f"⚠️  Low fill rate ({mapped_count}/{len(SECTION_KEYS)}) — check AI output headers match FORMAT_RULES")

        return parsed

    def normalize_ai_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        sections_data = raw.get("sections", {})
        doc_type      = raw.get("document_type", "guide")
        ai_images     = raw.get("images", [])

        normalized: Dict[str, Any] = {
            "title":               raw.get("title") or "",
            "subtitle":            raw.get("subtitle", ""),
            "document_type":       doc_type,
            "document_type_label": raw.get("document_type_label") or "",
            "sections_config":     self.SECTIONS,
            "framework":           {},
            "ai_images":           ai_images,
        }

        for key, default_title, default_label, _, _ in SECTIONS:
            sec_data = sections_data.get(key, {})
            if isinstance(sec_data, str):
                content = sec_data
                title   = default_title
            else:
                content = sec_data.get("content", "")
                title   = sec_data.get("title", "") or default_title

            if not content:
                logger.warning(f"⚠️  Empty section after mapping: {key}")

            sanitized = self._sanitize_html(str(content))
            sanitized = _strip_filler(sanitized)
            sanitized = _deduplicate_content(sanitized)

            normalized[key] = sanitized
            normalized["framework"][key] = {
                "title":  title or default_title,
                "kicker": default_label,
            }

            # Specialized extractions
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
            elif key == "conclusion":
                self._extract_cta(sanitized, normalized)

        normalized["summary"]             = normalized.get("executive_summary", "")[:500]
        normalized["cta_text"]            = normalized.get("conclusion", "")[:300]
        normalized["cta_headline"]        = normalized.get("cta_headline") or "Ready to Start Your Project?"
        normalized["legal_notice_summary"] = "This document provides strategic guidance and should be verified by a qualified professional."

        return normalized

    def _extract_intro_v2(self, html: str) -> str:
        """Extracts the first 2-3 sentences as an intro, cutting at a sentence boundary."""
        if not html:
            return ""
        # Remove headers and lists first
        clean = re.sub(r'<h[1-6]>.*?</h[1-6]>', '', html, flags=re.S)
        clean = re.sub(r'<ul>.*?</ul>', '', clean, flags=re.S)
        clean = re.sub(r'<ol>.*?</ol>', '', clean, flags=re.S)
        # Get first paragraph or first 300 chars
        match = re.search(r'<p>(.*?)</p>', clean, re.S)
        text = match.group(1) if match else clean
        text = re.sub(r'<[^>]+>', '', text).strip()
        
        if len(text) <= 250:
            return text
            
        # Find last sentence boundary before 250
        truncated = text[:250]
        # Find last ., !, or ?
        boundaries = [truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?')]
        last_boundary = max(boundaries)
        
        if last_boundary > 100: # Ensure we have at least some content
            return text[:last_boundary + 1]
        return truncated + "..."

    def _extract_bullets_v2(self, html: str) -> str:
        """Extracts 3-5 bullets and returns as HTML list items."""
        bullets = re.findall(r'<li>(.*?)</li>', html, re.S)
        if not bullets:
            # Try to find paragraphs that look like bullets
            paras = re.findall(r'<p>(?:•|-|\d\.)\s*(.*?)</p>', html, re.S)
            bullets = paras if paras else []
        
        # Take 3-5 bullets
        selected = bullets[:5]
        return "".join([f"<li>{b.strip()}</li>" for b in selected])

    def _extract_support_v2(self, html: str) -> str:
        """Extracts remaining paragraphs as plain-text support text."""
        paras = re.findall(r'<p>(.*?)</p>', html, re.S)
        # Skip the first paragraph (usually the intro)
        support_paras = [p for p in paras if not any(char in p[:5] for char in ['•', '-', '1.'])]
        if len(support_paras) > 1:
            # Strip tags and return plain text to avoid double-escaping
            clean_paras = [re.sub(r'<[^>]+>', '', p).strip() for p in support_paras[1:3]]
            return " ".join(clean_paras)
        return ""

    def _extract_callout_v2(self, html: str) -> str:
        """Extracts a bolded sentence or short paragraph as a callout."""
        match = re.search(r'<strong>(.*?)</strong>', html, re.S)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_stat_v2(self, html: str) -> tuple:
        """Extracts a statistic (value, label)."""
        if not html:
            return ("", "")
        
        # Look for percentages or numbers (e.g., 45%, $100k, 1,000)
        # We prioritize percentages and currency
        match = re.search(r'(\d+%\+?|\$\d+(?:\.\d+)?[MBK]?)', html)
        if not match:
            # Fallback to plain numbers if they look like a stat (at least 2 digits or followed by a keyword)
            match = re.search(r'(\d{2,}(?:,\d{3})*)', html)
            
        if match:
            val = match.group(1)
            # Find a label by looking at words around the value
            start = max(0, match.start() - 60)
            end = min(len(html), match.end() + 60)
            context = html[start:end]
            clean_context = re.sub(r'<[^>]+>', ' ', context).strip()
            
            keywords = ["efficiency", "increase", "roi", "savings", "growth", "reduction", "impact", "improvement"]
            for kw in keywords:
                if kw in clean_context.lower():
                    return (val, kw.title())
            
            return (val, "Key Metric")
        return ("", "")

    def _get_unsplash_url(self, keywords: str) -> str:
        """Returns empty string as we no longer support fake Unsplash URLs."""
        return ""

    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Dict[str, Any],
        signals: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        signals = signals or {}

        # ── Colours ─────────────────────────────────────────────────────────
        primary_color   = firm_profile.get("primary_brand_color") or signals.get("primary_color") or "#1a365d"
        secondary_color = firm_profile.get("secondary_brand_color") or "#c5a059"
        accent_color    = firm_profile.get("accent_color") or "#f8fafc"
        surface_color   = "#ffffff"
        on_surface      = "#1a202c"
        highlight_color = "#f4f7f9"

        # Ensure hex
        def fix_hex(c): return "#" + str(c).lstrip("#") if c and len(str(c).lstrip("#")) == 6 else "#1a365d"
        
        # ── Company info ─────────────────────────────────────────────────────
        company_name = (
            firm_profile.get("firm_name")
            or firm_profile.get("name")
            or signals.get("topic", "Strategic Analysis")
        )
        topic = signals.get("topic", "Industry Best Practices")
        doc_type_label = ai_content.get("document_type_label") or "STRATEGIC GUIDE"

        vars: Dict[str, Any] = {
            "primaryColor":      fix_hex(primary_color),
            "secondaryColor":    fix_hex(secondary_color),
            "accentColor":       fix_hex(accent_color),
            "surfaceColor":      fix_hex(surface_color),
            "onSurfaceColor":    fix_hex(on_surface),
            "highlightColor":    fix_hex(highlight_color),
            "documentTitle":     ai_content.get("title") or topic,
            "documentTypeLabel": doc_type_label,
            "mainTitle":         ai_content.get("title") or topic,
            "documentSubtitle":  ai_content.get("subtitle") or f"Strategic Insights and Implementation Roadmap for {topic}.",
            "companyName":       company_name,
            "emailAddress":      firm_profile.get("work_email", ""),
            "website":           firm_profile.get("firm_website", ""),
            "ctaHeadline":       "Ready to Start Your Project?",
            "contactDescription": "Contact us today for a consultation.",
            "cover_image_url":   self._get_unsplash_url(f"{topic},architecture,modern"),
            "contentsTitle":     "Table of Contents",
            "toc_html":          "",
        }

        # ── Section content vars ─────────────────────────────────────────────
        fw = ai_content.get("framework", {})
        ai_images = ai_content.get("ai_images", [])
        
        # Starting page for sections (Page 1: Cover, Page 2: TOC, Page 3: First Section)
        current_page = 3
        toc_html = ""

        for idx, (key, default_title, default_label, _, _) in enumerate(SECTIONS):
            sec_fw    = fw.get(key, {})
            sec_title = sec_fw.get("title") or default_title
            content   = ai_content.get(key, "")
            s_idx     = idx + 1

            # Extract granular components
            intro   = self._extract_intro_v2(content)
            bullets = self._extract_bullets_v2(content)
            support = self._extract_support_v2(content)
            callout = self._extract_callout_v2(content)
            stat_v, stat_l = self._extract_stat_v2(content)

            vars[f"customTitle{s_idx}"] = sec_title
            vars[f"section_{key}_intro_html"] = intro
            vars[f"section_{key}_bullets_html"] = bullets
            vars[f"section_{key}_support_html"] = support
            vars[f"section_{key}_callout"] = callout
            vars[f"section_{key}_stat_val"] = stat_v
            vars[f"section_{key}_stat_lbl"] = stat_l

            # Add to TOC HTML string instead of toc_items list
            num = str(s_idx).zfill(2)
            page_num = str(current_page).zfill(2)
            toc_html += f'<div class="toc-item"><span class="toc-num">{num}</span><span class="toc-label">{sec_title}</span><span class="toc-page">{page_num}</span></div>'
            current_page += 1

            # Image logic - Keyword based from section title and topic
            img_url = firm_profile.get(f"image_{s_idx}_url", "")
            if not img_url:
                # Use empty string if no user image is provided to suppress broken boxes
                img_url = ""
            
            vars[f"section_{key}_image_url"] = img_url
            vars[f"section_{key}_image_caption"] = f"{sec_title} - Strategic Visual Illustration"

        vars["toc_html"] = toc_html
        return vars

    # ─────────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────────────────────────────

    def _extract_intro(self, html: str) -> str:
        """Extracts the first few paragraphs as a plain-text intro."""
        if not html:
            return ""
        # Find all content before the first H3
        intro_part = re.split(r'<h[1-6]>', html, flags=re.I)[0]
        # Strip all tags and normalize whitespace
        clean = re.sub(r'<[^>]+>', ' ', intro_part)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean[:500] # Cap at 500 chars for template slots

    def _extract_subheadings(self, html: str) -> List[str]:
        return re.findall(r'<h3>(.*?)</h3>', html)

    def _extract_subcontent(self, html: str, subheading: str) -> str:
        pattern = rf'<h3>{re.escape(subheading)}</h3>\s*(.*?)(?:<h3>|$)'
        match   = re.search(pattern, html, re.S)
        if not match:
            return ""
        return re.sub(r'<[^>]+>', '', match.group(1).strip()).strip()[:400]

    def _extract_boxes(self, html: str) -> List[tuple]:
        matches = re.findall(r'<h3>(.*?)</h3>\s*(<p>.*?</p>|<ul>.*?</ul>)', html, re.S)
        return [(m[0], re.sub(r'<[^>]+>', '', m[1]).strip()) for m in matches]

    def _extract_stats(self, html: str, data: Dict):
        vals = re.findall(r'<li><strong>(.*?)</strong>\s*:?\s*(.*?)</li>', html, re.S)
        for i, (lbl, val) in enumerate(vals[:3]):
            data[f"stat{i+1}Value"] = re.sub(r'<[^>]+>', '', val).strip()
            data[f"stat{i+1}Label"] = re.sub(r'<[^>]+>', '', lbl).strip()

    def _extract_steps(self, html: str, data: Dict):
        steps = re.findall(r'<h3>Step \d+:\s*(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(steps[:5]):
            data[f"stepTitle{i+1}"]   = ttl.strip()
            data[f"stepContent{i+1}"] = re.sub(r'<[^>]+>', '', cnt).strip()

    def _extract_table(self, html: str, data: Dict):
        criteria = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(criteria[:4]):
            data[f"tableRow{i+1}Col1"] = ttl.strip()
            data[f"tableRow{i+1}Col2"] = re.sub(r'<[^>]+>', '', cnt).strip()[:150]

    def _extract_icons(self, html: str, data: Dict):
        themes = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(themes[:4]):
            clean = re.sub(r'<[^>]+>', '', cnt).strip()
            data[f"iconCard{i+1}Title"] = ttl.strip()
            data[f"iconCard{i+1}Text"]  = clean[:100] + ("..." if len(clean) > 100 else "")

    def _extract_timeline(self, html: str, data: Dict):
        phases = re.findall(r'<h3>Phase \d+:\s*(.*?)</h3>\s*<p>(.*?)</p>', html, re.S)
        for i, (ttl, cnt) in enumerate(phases[:5]):
            data[f"timelineItem{i+1}Title"] = ttl.strip()
            data[f"timelineItem{i+1}"]      = re.sub(r'<[^>]+>', '', cnt).strip()

    def _extract_checklists(self, html: str, data: Dict, prefix: str, limit: int):
        items = re.findall(r'<li>(.*?)</li>', html, re.S)
        for i, itm in enumerate(items[:limit]):
            data[f"{prefix}{i+1}"] = re.sub(r'<[^>]+>', '', itm).strip()

    def _extract_cta(self, html: str, data: Dict):
        match = re.search(r'<h3>(.*?)</h3>', html)
        if match:
            data["ctaHeadline"] = match.group(1).strip()

    def render_image(self, url: str, alt: str = "", aspect_ratio: str = "16/9", lazy: bool = True) -> str:
        """
        Returns a responsive <picture> element with placeholder and CLS prevention.
        """
        # If no URL, use a high-quality architectural placeholder
        if not url:
            url = "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&q=80&w=1000"
        
        loading_attr = 'loading="lazy"' if lazy else ""
        
        # Use an inline SVG placeholder to reserve space (CLS prevention)
        # Assuming 16:9 aspect ratio by default
        w, h = map(int, aspect_ratio.split('/'))
        placeholder = f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}'%3E%3C/svg%3E"
        
        return f"""
        <picture class="img-container" style="aspect-ratio: {aspect_ratio};">
            <source srcset="{url}" type="image/webp">
            <img src="{placeholder}" data-src="{url}" alt="{alt}" {loading_attr} 
                 class="lazyload" style="width:100%; height:auto; display:block;">
        </picture>
        """

    def _sanitize_html(self, html: str) -> str:
        if not html:
            return html
        html = html.strip().strip('"')

        def _replace_tag(m):
            tag = m.group(2).lower()
            return m.group(0) if tag in ALLOWED_TAGS else ""

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
            return json.loads(response.choices[0].message.content)
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

    def ensure_section_content(
        self, sections: list, signals: Dict[str, Any], firm_profile: Dict[str, Any]
    ) -> list:
        """Pass-through — backward compat with FormaAIConversationView."""
        return sections
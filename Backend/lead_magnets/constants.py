# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT SECTION DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SECTIONS = [
    (
        "introduction",
        "Executive Summary",
        "EXECUTIVE SUMMARY",
        "text-only",
        (
            "Write a high-impact Executive Summary for a strategic report on {topic} for {audience}.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MAX 150 words.\n"
            "  • Summarize core findings and strategic value proposition immediately.\n"
            "  • Achieve high information density (at least 1 insight per 100 words).\n"
            "  • Include a 'KEY INSIGHT' callout.\n"
            "  • No generic filler. Use objective, research-backed tone.\n"
            "  • End with a transition to the next section: 'Market Dynamics & Industry Challenges'.\n"
        )
    ),
    (
        "industry_challenges",
        "Industry Challenges",
        "CHALLENGES",
        "image-right",
        (
            "Analyze 4 critical industry challenges regarding {topic} that impact {audience}.\n"
            "TONE: Analytical, focusing on risks and regulatory complexities.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 150–180 words.\n"
            "  • Focus on hidden costs, regulatory traps (NCC, BASIX), and technical barriers.\n"
            "  • Include an 'INDUSTRY STAT' callout using [INDUSTRY STAT: text] format.\n"
            "  • No filler phrases.\n"
            "STRUCTURE:\n"
            "<h3>[Specific Challenge Name]</h3>\n"
            "<p>Explain the systemic issue and its financial or operational impact.</p>\n"
            "[INDUSTRY STAT: A specific percentage or metric related to this challenge.]"
        )
    ),
    (
        "core_principles",
        "Core Principles",
        "PRINCIPLES",
        "image-left",
        (
            "Define the 3 foundational pillars of successful {topic} implementation.\n"
            "TONE: Advisory and principled.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 150–180 words.\n"
            "  • Use architectural analogies and technical standards (Passive House, LEED).\n"
            "  • Include a 'STRATEGIC TIP' callout using [STRATEGIC TIP: text] format.\n"
            "STRUCTURE:\n"
            "<h3>[Principle Name]</h3>\n"
            "<p>Technical explanation of the principle and its long-term benefit.</p>\n"
            "[STRATEGIC TIP: Actionable advice for immediate implementation.]"
        )
    ),
    (
        "practical_strategies",
        "Practical Design Strategies",
        "STRATEGIES",
        "text-only",
        (
            "Provide 3-4 high-impact design strategies for {topic}.\n"
            "TONE: Technical and practical.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 150–180 words.\n"
            "  • Focus on building envelope efficiency, renewable integration, and thermal mass.\n"
            "  • Include a [IMAGE: description] block indicating where a diagram should go.\n"
            "STRUCTURE:\n"
            "<h3>[Strategy Name]</h3>\n"
            "<p>Detailed 'how-to' explanation with expected ROI or performance metrics.</p>\n"
            "[IMAGE: Technical diagram of this design strategy in practice]"
        )
    ),
    (
        "risk_management",
        "Risk Management",
        "RISK",
        "image-above",
        (
            "Outline the risk mitigation framework for {topic} projects.\n"
            "TONE: Risk-averse and professional.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 120–150 words.\n"
            "  • Identify non-obvious risks (liability, maintenance, supply chain).\n"
            "  • Include a 'KEY INSIGHT' callout.\n"
            "STRUCTURE:\n"
            "<h3>[Risk Category]</h3>\n"
            "<p>Analysis of the risk and the professional mitigation strategy required.</p>\n"
            "[KEY INSIGHT: The most critical risk factor to monitor.]"
        )
    ),
    (
        "best_practices",
        "Best Practices",
        "TIPS",
        "text-only",
        (
            "Distill 'insider' best practices from top-tier architectural consultancies.\n"
            "TONE: Sophisticated and elite.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 150–180 words.\n"
            "  • Focus on quality assurance and project lifecycle management.\n"
            "  • Include a 'STRATEGIC TIP' callout.\n"
            "STRUCTURE:\n"
            "<h3>[Best Practice Name]</h3>\n"
            "<p>The high-level strategy and its impact on project success.</p>\n"
            "[STRATEGIC TIP: A specific checklist item for the project manager.]"
        )
    ),
    (
        "key_statistics",
        "Key Statistics",
        "DATA",
        "text-only",
        (
            "Present data-driven insights on the ROI and impact of {topic}.\n"
            "TONE: Fact-based and quantitative.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 120–150 words.\n"
            "  • Use verifiable-style metrics (e.g., '22% reduction in lifecycle costs').\n"
            "  • Include an 'INDUSTRY STAT' callout.\n"
            "STRUCTURE:\n"
            "<h3>Economic & Environmental Impact</h3>\n"
            "<ul><li>[Data point with explanation]</li></ul>\n"
            "[INDUSTRY STAT: The single most impressive data point.]"
        )
    ),
    (
        "implementation_roadmap",
        "Implementation Roadmap",
        "ROADMAP",
        "text-only",
        (
            "Define a 5-phase strategic timeline for {topic} projects.\n"
            "TONE: Process-oriented and structured.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 150–180 words.\n"
            "  • Focus on the transition from vision to handover.\n"
            "  • Include a [IMAGE: roadmap diagram] block.\n"
            "STRUCTURE:\n"
            "<h3>[Phase Name]</h3>\n"
            "<p>Critical path tasks and stakeholder requirements for this phase.</p>\n"
            "[IMAGE: Visual roadmap showing the 5-phase progression]"
        )
    ),
    (
        "traditional_vs_modern",
        "Traditional vs. Modern Approaches",
        "COMPARISON",
        "text-only",
        (
            "Compare legacy building methods with modern, high-performance approaches.\n"
            "TONE: Comparative and objective.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 150–180 words.\n"
            "  • Contrast 'business as usual' with 'innovation-led' design.\n"
            "  • Include a 'KEY INSIGHT' callout.\n"
            "STRUCTURE:\n"
            "<h3>[Comparison Point]</h3>\n"
            "<p>Analysis of the shift in industry standards and the benefit of modernization.</p>\n"
            "[KEY INSIGHT: Why the modern approach is the only logical choice for long-term value.]"
        )
    ),
    (
        "case_study",
        "Real-World Case Study",
        "CASE STUDY",
        "text-only",
        (
            "Present a detailed success story illustrating {topic} in practice.\n"
            "TONE: Narrative but data-heavy.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 180–200 words.\n"
            "  • Detail the Challenge, the Unique Mechanism used, and the quantifiable Transformation.\n"
            "  • Include an 'INDUSTRY STAT' callout.\n"
            "STRUCTURE:\n"
            "<h3>Project: [Fictional High-End Project Name]</h3>\n"
            "<p><strong>Challenge:</strong> Complex technical barrier.</p>\n"
            "<p><strong>Solution:</strong> Innovative application of {topic}.</p>\n"
            "<p><strong>Result:</strong> Specific performance metrics (cost, energy, time).</p>\n"
            "[INDUSTRY STAT: Performance improvement metric achieved in this case.]"
        )
    ),
    (
        "expert_insights",
        "Expert Insights",
        "INSIGHTS",
        "text-only",
        (
            "Provide high-level expert answers to sophisticated questions about {topic}.\n"
            "TONE: Intellectual and advisory.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 150–180 words.\n"
            "  • Avoid basic FAQs; focus on 'edge case' complexities.\n"
            "  • Include a 'STRATEGIC TIP' callout.\n"
            "STRUCTURE:\n"
            "<h3>Expert Perspective: [Complex Question]</h3>\n"
            "<p>A nuanced answer referencing industry standards or future trends.</p>\n"
            "[STRATEGIC TIP: Expert advice on navigating this complexity.]"
        )
    ),
    (
        "conclusion",
        "Next Steps",
        "NEXT STEPS",
        "text-only",
        (
            "Create a powerful closing statement that positions the firm as the ideal partner.\n"
            "TONE: Persuasive, elite, and inviting.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • 120–150 words.\n"
            "  • Summarize the path forward.\n"
            "  • Focus on partnership and expertise.\n"
            "STRUCTURE:\n"
            "<h3>Partnering for Success</h3>\n"
            "<p>A final persuasive paragraph on why now is the time to act and why this firm is the logical choice.</p>\n"
            "<h3>Ready to Start?</h3>\n"
            "<p>A clear, sophisticated call to action.</p>"
        )
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT DOC TYPE LABELS
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_DOC_TYPE_LABELS = {
    "guide":             "Strategic Guide",
    "case_study":        "Case Study Report",
    "checklist":         "Implementation Checklist",
    "roi_calculator":    "ROI Analysis Report",
    "trends_report":     "Industry Trends Report",
    "design_portfolio":  "Design Portfolio",
    "client_onboarding": "Client Onboarding Guide",
    "custom":            "Strategic Report",
}

# ─────────────────────────────────────────────────────────────────────────────
# MASTER PROMPT — high-density executive-grade content generation
# ─────────────────────────────────────────────────────────────────────────────
MASTER_PROMPT_TEMPLATE = """
You are an elite research writer and subject-matter expert for high-end consultancies.
Your task is to generate a PREMIUM, HIGH-DENSITY lead magnet that delivers maximum value with zero filler.

CRITICAL DIRECTIVES:
1. EXECUTIVE SUMMARY (PAGE 4): Instead of an introduction, start with a high-impact 'Executive Summary' (max 150 words) that outlines key findings and strategic value immediately.
2. INFORMATION DENSITY: Maintain a minimum of one core strategic insight or actionable takeaway per 100 words. No generic statements or repetition.
3. DOMAIN EXPERTISE: Use sophisticated vocabulary and reference latest data (≤ 12 months old) and authoritative sources (e.g., NCC 2022, IPCC reports, McKinsey Research). Use inline citations where possible.
4. STRUCTURE: Use a logical, hierarchical progression: Problem Definition → Deep Analysis → Proposed Solution → Implementation Framework → Quantifiable Results.
5. TRANSITIONS: Each section MUST end with a transition paragraph that links to the next section to ensure narrative coherence.
6. NO FIRST-PERSON: Maintain an objective, institutional tone throughout.
7. HIGHLIGHT BOXES: Include exactly one highlight box per section:
   [KEY INSIGHT: text]
   [STRATEGIC TIP: text]
   [INDUSTRY STAT: text]

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
- Use <h1> for the section title (H1).
- Use <h2> for major sub-points (H2).
- Use <h3> for detailed breakdowns (H3).
- Use <p> for body text.
- Use <ul><li> for lists.
- Output MUST be structured with Markdown headers for internal mapping:
  # [Keyword-Rich Main Title]
  ## [Section Name]
  [Section Content with H2, H3, Transition Paragraphs, and Highlight Boxes]

Do NOT include any introductory remarks. Only output the lead magnet content.
"""

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT FORMAT RULES
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_FORMAT_RULES = {
    "guide": """
Structure (use these EXACT ## header names):
## Introduction
## Common Challenges
## Key Principles
## Practical Strategies
## Managing Risks
## Best Practices
## Facts and Figures
## Implementation Roadmap
## Traditional vs Modern
## Key Lessons
## Real World Example
## Expert Insights
## Ready to Start
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
## Expert Insights
## Ready to Start
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
# DEFAULT TERMS OF USE
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_TERMS = {
    "title":        "Terms of Use & Disclaimer",
    "summary":      "This document is provided for informational and strategic guidance purposes only.",
    "paragraph1":   "The content within this lead magnet, including all architectural insights, strategic recommendations, and data points, is generated with the assistance of artificial intelligence and should be verified by a licensed professional before implementation.",
    "paragraph2":   "Your use of this document does not constitute an architect-client relationship. All project-specific decisions should be made in consultation with qualified experts familiar with your local building codes and site conditions.",
    "paragraph3":   "We make no warranties, expressed or implied, regarding the accuracy or completeness of the information provided. The architectural standards referenced (e.g., NCC, Passive House) are subject to change and local interpretation.",
    "paragraph4":   "Unauthorized reproduction or distribution of this material is prohibited. All trademarks and registered marks are the property of their respective owners.",
    "paragraph5":   "© 2024 All Rights Reserved.",
}

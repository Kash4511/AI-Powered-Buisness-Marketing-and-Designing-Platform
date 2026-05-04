# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT SECTION DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SECTIONS = [
    (
        "introduction",
        "Introduction",
        "OVERVIEW",
        "text-only",
        (
            "Write a high-impact Introduction and Executive Summary.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards (e.g. NCC, Passive House) and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "industry_challenges",
        "Common Challenges",
        "CHALLENGES",
        "text-only",
        (
            "Analyze the critical industry challenges.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "core_principles",
        "Key Principles",
        "PRINCIPLES",
        "text-only",
        (
            "Define the core design principles.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "practical_strategies",
        "Practical Strategies",
        "STRATEGIES",
        "text-only",
        (
            "Provide actionable design strategies.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "risk_management",
        "Managing Risks",
        "RISK",
        "text-only",
        (
            "Outline risk mitigation frameworks.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "best_practices",
        "Best Practices",
        "TIPS",
        "text-only",
        (
            "Distill elite best practices.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "key_statistics",
        "Facts and Figures",
        "DATA",
        "text-only",
        (
            "Present data-driven insights.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "implementation_roadmap",
        "Implementation Roadmap",
        "ROADMAP",
        "text-only",
        (
            "Define the strategic timeline.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "traditional_vs_modern",
        "Traditional vs Modern",
        "COMPARISON",
        "text-only",
        (
            "Compare legacy vs modern approaches.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "case_study",
        "Real World Example",
        "CASE STUDY",
        "text-only",
        (
            "Provide a detailed client success story.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "expert_insights",
        "Expert Insights",
        "INSIGHTS",
        "text-only",
        (
            "Provide high-level expert analysis.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Cite specific standards and real numbers.\n"
            "  • End with a transition to the next section.\n"
        )
    ),
    (
        "conclusion",
        "Ready to Start",
        "NEXT STEPS",
        "text-only",
        (
            "Create a powerful call to action.\n"
            "CONTENT REQUIREMENTS:\n"
            "  • MINIMUM 300 words.\n"
            "  • 3–5 full paragraphs, each 80–120 words.\n"
            "  • Summarize why the firm is the logical choice.\n"
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
MASTER_PROMPT_TEMPLATE = """You are a senior architectural consultant writing a premium lead magnet for a specific firm and their ideal clients. This is NOT a generic document — every paragraph must reference the topic, audience, and pain points provided below. 

HARD RULES — VIOLATION = REJECTION: 
1. OUTPUT FORMAT: Use ONLY `# Title: Subtitle` at the top, then `## Section Name` headers, then raw HTML inside each section. No markdown bold (**), no markdown headers (###), no [BRACKETS], no # inside section content. 
2. ZERO SHORT SECTIONS: Every ## section must contain a MINIMUM of 300 words. A section with fewer than 300 words will be rejected. If you cannot fill a section, add more specific examples, case studies, or data points until it reaches 300 words. 
3. ZERO PLACEHOLDER TEXT: Never write [INDUSTRY STAT: ...] or [EXAMPLE] or any bracketed placeholder. If you reference a statistic, write the full sentence with the actual number. Never truncate mid-sentence. 
4. ZERO GENERIC OPENERS: Never start a section with "So,", "Another", "While", "One of the most", "At our firm, we believe", "Our team", "We recommend". Start every section with a specific, provocative claim, a named standard, or a concrete number. 
5. SECTION TITLES MUST MATCH: Use EXACTLY the section names listed in the FORMAT RULES below. Do not invent new section names like "Competitive Landscape" or "Technological Complexity". 
6. NO FIRST-PERSON FIRM VOICE: Never write "our firm", "we believe", "we have worked". Write as an independent expert adviser speaking directly to the reader. 
7. SPECIFIC STANDARDS REQUIRED: Every section must name at least one specific standard, regulation, or certification relevant to the topic — e.g., NCC Section J, BASIX certificate, Passive House PHI certification, NABERS 5-star, LEED Platinum, AS 1428, BCA compliance, local zoning codes. 
8. REAL NUMBERS REQUIRED: Every section must contain at least one specific quantified claim — e.g., "up to 72% reduction in heating load", "$180,000 in lifecycle savings over 25 years", "15–20% premium on property value". 

CONTENT DEPTH — NON-NEGOTIABLE: 
- Each ## section: 3–5 full paragraphs, each 80–120 words 
- Each paragraph delivers ONE distinct insight — no repetition across paragraphs 
- Include a <ul> list of 3–5 items where relevant, each item 20+ words 
- Total document: minimum 3,500 words across all sections 

TOPIC PERSONALISATION REQUIREMENT: 
Every paragraph must weave in the Topic, Audience, and Pain Points below. The reader must feel this was written specifically for them, not copied from a generic architecture textbook. 

INPUT: 
Topic: {topic} 
Lead Magnet Type: {lead_magnet_type} 
Audience: {audience} 
Pain Points: {pain_points} 
Psychographics: {psychographics} 
Firm USP: {firm_usp} 

FORMAT RULES — USE THESE EXACT ## HEADERS: 
{format_specific_rules} 

HTML FORMATTING INSIDE SECTIONS: 
Use ONLY these tags: <p>, <h3>, <strong>, <ul>, <li> 
- <p> for paragraphs 
- <h3> for sub-headings within a section (NOT markdown ###) 
- <strong> for emphasis on a specific term or number 
- <ul><li> for bullet lists 

EXAMPLE OF CORRECT OUTPUT FORMAT: 
# The High-Performance Building Playbook: A Strategic Guide for Government Developers 
## Introduction 
<p>Buildings account for <strong>39% of global carbon emissions</strong> — and the regulatory frameworks forcing developers to act are tightening faster than most project timelines allow.</p> 
<h3>Why NCC Section J Compliance Is No Longer Optional</h3> 
<p>The 2022 update to Section J of the National Construction Code mandates a minimum 7-star NatHERS rating for Class 1 buildings, up from 6 stars. For government developers managing multiple concurrent projects, this isn't an administrative footnote — it's a design constraint that reshapes procurement, envelope specifications, and M&E budgets from day one.</p> 

OUTPUT: Only the document content. No preamble. No sign-off. No [IMAGE] blocks. No placeholder text of any kind."""

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
## Real World Example
## Expert Insights
## Ready to Start
""",
    "checklist": """
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
## Real World Example
## Expert Insights
## Ready to Start
""",
    "case_study": """
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
## Real World Example
## Expert Insights
## Ready to Start
""",
    "roi_calculator": """
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
## Real World Example
## Expert Insights
## Ready to Start
""",
    "trends_report": """
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
## Real World Example
## Expert Insights
## Ready to Start
""",
    "client_onboarding": """
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
## Real World Example
## Expert Insights
## Ready to Start
""",
    "design_portfolio": """
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
## Real World Example
## Expert Insights
## Ready to Start
""",
    "custom": """
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
## Real World Example
## Expert Insights
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

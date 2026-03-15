# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT SECTION DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SECTIONS = [
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
        "expert_insights",
        "Expert Insights & FAQs",
        "INSIGHTS",
        "text-only",
        (
            "Provide 3-4 frequently asked questions about {topic} with expert answers.\n"
            "STRUCTURE:\n"
            "<h3>Expert Insight: [Question Name]</h3>\n"
            "<p>The question explained simply.</p>\n"
            "<p><strong>The Answer:</strong> Expert advice based on industry standards.</p>\n"
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
            "<p>Encouraging advice and a specific invitation to consult.\n"
            "TARGET: 250–300 words."
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
# DEFAULT MASTER PROMPT
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_MASTER_PROMPT_TEMPLATE = """
You are a senior architectural consultant and high-end marketing strategist. 
Your task is to generate a SUBSTANTIAL, HIGH-VALUE lead magnet that sounds like it was written by a human expert with 20+ years of experience.

CRITICAL DIRECTIVES:
1. NO FIRST-PERSON FIRM VOICE: BANNED phrases include "our firm", "we believe", "we recommend", "we specialize in". Use an objective, authoritative tone or address the reader directly.
2. NO TRANSITIONAL SLOP: BANNED openers include "So,", "Another", "While", "Furthermore,", "In addition to". Start every paragraph with a direct, impactful claim or data point.
3. PROVOCATIVE OPENERS: Every section MUST open with a provocative claim, a surprising data point, or a sharp industry insight. No soft setups or "Introduction to..." sentences.
4. SPECIFIC STANDARDS: You MUST reference named architectural and building standards where relevant (e.g., Passive House, NCC, LEED, NABERS, BASIX, WELL Building Standard). 
5. DATA-DRIVEN: You MUST include specific numbers, percentages, or cost-benefit metrics in EVERY section. (e.g., "A 15% reduction in thermal bridging leads to...", "The NCC 2022 updates require...").
6. HYPER-SPECIFICITY: Replace generic advice with precise, actionable insights. Use real-world analogies and concrete metrics.
7. NO REPETITION: Ensure each section provides unique value. Do not repeat the same points across different headers.

CONTENT DEPTH REQUIREMENTS:
- The guide must contain substantial content.
- Rules:
  • Each major section must contain 3–5 paragraphs.
  • Each paragraph should be 80–120 words.
  • Include bullet lists where helpful.
  • Provide examples or explanations when introducing ideas.
  • Avoid one-line sections or short filler text.
- Minimum structure for each section:
  Section Title
  Provocative opening sentence with data or a sharp claim.
  Paragraph explaining the strategic implications.
  Paragraph detailing technical requirements or standards (NCC, Passive House, etc.).
  Bullet list of practical, non-obvious considerations.
  Detailed scenario or metric-based explanation.

IMAGE PLACEMENT RULES:
- Images must not appear randomly inside text.
- Use this format for images:
  [IMAGE]
  Type: illustration / diagram / architecture / sustainability
  Description: short description
  Placement: after section header
  [/IMAGE]

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

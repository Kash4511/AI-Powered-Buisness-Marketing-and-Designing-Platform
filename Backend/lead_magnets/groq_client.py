mport os
import json
import logging
import time
import re
from typing import Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT TYPE CONFIGURATIONS
# Each type defines: page structure, tone, section schema, and content density
# ─────────────────────────────────────────────────────────────────────────────
DOCUMENT_TYPE_CONFIGS = {
    "guide": {
        "label": "Strategic Guide",
        "tone": "authoritative, analytical, institutional",
        "structure_description": "15-page deep-dive consulting guide with executive summary, technical analysis, frameworks, case studies, and actionable roadmap",
        "sections": [
            ("executive_summary",        "Executive Summary",          "STRATEGY",    "800-word executive-level overview. What the problem is, why it matters now, what this guide delivers. Include ROI context and strategic urgency. No filler."),
            ("market_landscape",         "Market Landscape",           "MARKET",      "900-word analysis of the current state of {topic} in {industry}. Include market pressures, emerging shifts, and why {audience} must act. Cite plausible market dynamics and real patterns."),
            ("core_challenge_1",         "{topic}: Challenge 1",       "ANALYSIS",    "1000-word deep technical analysis of the first major challenge in {topic} for {audience}. Root causes, mechanisms, financial/operational impact. Data-driven, no generics."),
            ("core_challenge_2",         "{topic}: Challenge 2",       "ANALYSIS",    "1000-word deep technical analysis of the second major challenge. Specific to {pain_points}. Include quantified risk exposure and failure modes."),
            ("core_challenge_3",         "{topic}: Challenge 3",       "ANALYSIS",    "1000-word analysis of the third challenge. Focus on systemic causes and downstream consequences for {audience}. Tie directly to {pain_points}."),
            ("strategic_framework",      "Strategic Framework",        "FRAMEWORK",   "1000-word proprietary framework for solving {topic}. Name the framework. Define 4-5 phases or pillars. Each pillar gets 150-200 words of substance. Make it feel like a real consulting methodology."),
            ("audience_playbook_1",      "Commercial Stakeholder Playbook", "PLAYBOOK", "800-word section written specifically for commercial/institutional stakeholders in {audience}. Concrete steps, financial logic, decision criteria."),
            ("audience_playbook_2",      "Technical Practitioner Playbook", "PLAYBOOK", "800-word section for technical practitioners (architects, engineers, contractors). Implementation steps, tools, coordination protocols."),
            ("audience_playbook_3",      "Public Sector Playbook",     "PLAYBOOK",    "800-word section for government/regulatory audiences. Policy levers, approval acceleration, ESG alignment, PPP models."),
            ("risk_governance",          "Risk & Governance",          "RISK",        "900-word section on risk allocation, contractual frameworks, contingency planning, and liability management specific to {topic}."),
            ("financial_modeling",       "Financial Modeling",         "FINANCIAL",   "900-word section with IRR analysis, CapEx sensitivity, cost-benefit modeling, and financing instruments relevant to {topic} for {audience}."),
            ("case_studies",             "Case Studies",               "EVIDENCE",    "1000-word section with 2 detailed case studies. Each: context, challenge, intervention, measurable outcome. Specific numbers. Real-feeling scenarios tied to {topic}."),
            ("implementation_roadmap",   "Implementation Roadmap",     "ROADMAP",     "900-word phased roadmap. Phase 1: Discovery & Audit (weeks 1-4). Phase 2: Design & Planning (weeks 5-10). Phase 3: Execution (weeks 11-24). Phase 4: Optimization. Each phase: objectives, deliverables, KPIs."),
            ("performance_dashboard",    "Performance Dashboard",      "OUTCOMES",    "800-word KPI framework. Before/after benchmarks, 8-10 specific metrics with target values, measurement methodology, reporting cadence."),
            ("final_recommendations",    "Final Recommendations",      "CONCLUSION",  "600-word authoritative conclusion. Top 5 prioritized recommendations, 90-day quick wins, 12-month strategic agenda, ROI forecast."),
        ]
    },
    "case_study": {
        "label": "Case Study Report",
        "tone": "evidence-based, precise, outcome-focused",
        "structure_description": "15-page institutional case study with project context, challenge analysis, intervention methodology, phased execution, and quantified outcomes",
        "sections": [
            ("executive_summary",        "Executive Summary",          "OVERVIEW",    "700-word executive brief: project type, core challenge, methodology used, headline outcomes. Written for a C-suite reader deciding whether to replicate this approach."),
            ("project_context",          "Project Context",            "CONTEXT",     "900-word detailed project background. Asset type, location context, ownership structure, strategic objectives, baseline conditions, and constraints. Specific and grounded."),
            ("challenge_diagnosis",      "Challenge Diagnosis",        "CHALLENGE",   "1000-word forensic analysis of the problems faced. Root cause mapping, failure point identification, risk exposure at project outset. Technical and financial dimensions."),
            ("stakeholder_landscape",    "Stakeholder Landscape",      "STAKEHOLDERS","800-word mapping of all stakeholders: owner, authority, design team, contractor, end-users. How misalignment manifested. What was at stake for each party."),
            ("methodology_overview",     "Intervention Methodology",   "METHOD",      "1000-word description of the strategic approach taken. Why this methodology was chosen over alternatives. The logic of each decision."),
            ("phase_1_execution",        "Phase 1: Discovery",         "EXECUTION",   "900-word account of Phase 1. What was found, what was unexpected, how the team responded. Specific findings with numbers."),
            ("phase_2_execution",        "Phase 2: Design & Planning", "EXECUTION",   "900-word account of Phase 2. Design decisions, coordination mechanisms, approval strategy, value engineering choices."),
            ("phase_3_execution",        "Phase 3: Delivery",          "EXECUTION",   "900-word account of delivery phase. Trade sequencing, issue resolution, change management, quality milestones."),
            ("risk_events",              "Risk Events & Responses",    "RISK",        "800-word section on specific risk events encountered. How each was identified, escalated, and resolved. Contractual mechanisms used."),
            ("financial_performance",    "Financial Performance",      "FINANCIAL",   "900-word financial analysis. Budget vs actuals, change order volume, IRR achieved vs target, CapEx efficiency, financing cost management."),
            ("esg_outcomes",             "ESG & Social Outcomes",      "ESG",         "800-word section on environmental, social, and governance outcomes. Carbon savings, community impact, regulatory compliance achieved."),
            ("lessons_learned",          "Lessons Learned",            "INSIGHTS",    "900-word honest debrief. What worked, what didn't, what would be done differently. Specific actionable insights for replication."),
            ("replication_framework",    "Replication Framework",      "FRAMEWORK",   "900-word section: how to replicate this project's success. Prerequisites, decision criteria, team structure, timeline expectations."),
            ("performance_dashboard",    "Performance Dashboard",      "OUTCOMES",    "800-word full KPI summary. 10+ metrics with baseline vs outcome. Visual-ready data points."),
            ("final_recommendations",    "Strategic Recommendations",  "CONCLUSION",  "600-word conclusion for stakeholders considering similar projects. Top 5 recommendations with rationale and risk-adjusted ROI estimate."),
        ]
    },
    "checklist": {
        "label": "Implementation Checklist",
        "tone": "precise, actionable, practitioner-grade",
        "structure_description": "15-page implementation checklist with phase-by-phase verification items, decision gates, risk checkpoints, and completion criteria",
        "sections": [
            ("executive_summary",        "How to Use This Checklist",  "OVERVIEW",    "700-word guide on how to use this checklist. Who should use it, when, in what sequence. Decision gates explained. How to handle incomplete items."),
            ("pre_project_checklist",    "Pre-Project Verification",   "PHASE 0",     "900-word comprehensive pre-project checklist. 15-20 specific verification items across: mandate clarity, budget approval, team assembly, site due diligence, regulatory pre-consultation. Each item gets 2-3 sentences of guidance."),
            ("site_assessment",          "Site & Technical Assessment","PHASE 1",     "900-word site assessment checklist. Structural surveys, hazardous material screening, MEP condition audit, heritage assessment, planning constraints. Specific items with pass/fail criteria."),
            ("design_checklist",         "Design & Documentation",     "PHASE 2",     "900-word design phase checklist. BIM requirements, LOD specifications, coordination meetings, consultant appointments, heritage consent, planning submission items."),
            ("procurement_checklist",    "Procurement & Contracting",  "PHASE 3",     "900-word procurement checklist. Tender documents, contractor selection criteria, contract form selection, insurance requirements, bond requirements, program verification."),
            ("approval_checklist",       "Regulatory Approvals",       "APPROVALS",   "900-word approvals checklist. Building consent, planning permission, heritage consent, fire engineering, accessibility compliance. Each with responsible party and typical timeline."),
            ("mobilisation_checklist",   "Site Mobilisation",          "PHASE 4",     "800-word pre-construction mobilisation checklist. Site establishment, safety plan, logistics plan, utility isolation, neighbour notification, hoarding permits."),
            ("early_works_checklist",    "Early Works Execution",      "PHASE 5",     "900-word early works checklist. Abatement, strip-out, structural opening-up, service disconnection. Hold points and sign-off requirements for each stage."),
            ("main_works_checklist",     "Main Works Execution",       "PHASE 6",     "900-word main works checklist by trade. Structural, envelope, MEP rough-in, fit-out sequencing. Inspection hold points. Coordination items between trades."),
            ("quality_checklist",        "Quality Assurance Gates",    "QA/QC",       "800-word QA checklist. Inspection and test plan items, defect management process, third-party verification requirements, photographic documentation standards."),
            ("risk_register",            "Risk Register Checklist",    "RISK",        "900-word active risk management checklist. 15 specific risks for {topic} projects with likelihood, impact, mitigation action, and monitoring frequency."),
            ("handover_checklist",       "Practical Completion",       "PHASE 7",     "900-word handover checklist. Defects inspection, O&M manuals, as-built drawings, commissioning certificates, warranty registration, training completion."),
            ("post_occupancy",           "Post-Occupancy Review",      "PHASE 8",     "800-word post-occupancy checklist. 6-week review items, 6-month performance checks, ESG metric verification, tenant satisfaction, lessons-learned documentation."),
            ("compliance_tracker",       "Compliance & Reporting",     "COMPLIANCE",  "800-word ongoing compliance checklist. Planning conditions discharge, building warrant of fitness, ESG reporting, insurance renewals, lease compliance."),
            ("final_recommendations",    "Checklist Master Summary",   "SUMMARY",     "600-word master summary. Critical path items, most commonly missed items, decision gate summary, escalation protocol."),
        ]
    },
    "roi_calculator": {
        "label": "ROI Analysis Report",
        "tone": "financial, quantitative, investment-grade",
        "structure_description": "15-page ROI analysis with financial modeling, sensitivity analysis, risk-adjusted returns, and institutional investment framework",
        "sections": [
            ("executive_summary",        "Investment Summary",         "OVERVIEW",    "700-word investment-grade executive summary. Headline ROI metrics, investment thesis, key assumptions, risk-adjusted return range. Written for an investment committee."),
            ("market_opportunity",       "Market Opportunity",         "MARKET",      "900-word market sizing and opportunity analysis. TAM/SAM/SOM for {topic}. Demand drivers, supply constraints, pricing dynamics, entry timing rationale."),
            ("baseline_financials",      "Baseline Financial Model",   "FINANCIALS",  "1000-word baseline financial model walkthrough. Revenue assumptions, cost structure, CapEx requirements, operating cost projections, depreciation schedule."),
            ("roi_calculation",          "ROI Calculation Methodology","ROI",         "1000-word detailed ROI calculation. IRR, NPV, payback period, cash-on-cash return, equity multiple. Step-by-step methodology with assumptions clearly stated."),
            ("capex_analysis",           "CapEx Deep Dive",            "CAPEX",       "900-word CapEx analysis. Hard costs, soft costs, contingency, financing costs, pre-development costs. Benchmarks vs comparable projects."),
            ("revenue_modeling",         "Revenue & NOI Modeling",     "REVENUE",     "900-word revenue model. Rental rate assumptions, occupancy projections, lease structure, escalation clauses, vacancy and credit loss. NOI build-up."),
            ("sensitivity_analysis",     "Sensitivity Analysis",       "RISK",        "1000-word sensitivity analysis. IRR sensitivity to: rental rates (±10%, ±20%), CapEx overrun (±15%), timeline slippage (3/6/12 months), vacancy rate (5/10/15%). Tornado chart data."),
            ("financing_structure",      "Financing Structure",        "FINANCING",   "900-word financing analysis. Debt vs equity split, LTV rationale, interest rate assumptions, green bond eligibility, brownfield tax credits, government grants."),
            ("risk_adjusted_returns",    "Risk-Adjusted Returns",      "RISK",        "900-word risk-adjusted analysis. Monte Carlo scenario ranges, downside protection, upside capture, probability-weighted IRR. Conservative/base/optimistic cases."),
            ("esg_value",                "ESG Value Premium",          "ESG",         "800-word ESG financial value. Green premium on rents, lower financing costs via green bonds, carbon credit value, reduced regulatory risk, tenant retention premium."),
            ("exit_strategy",            "Exit Strategy Analysis",     "EXIT",        "900-word exit analysis. Hold vs sell decision framework, exit cap rate assumptions, value-add vs core repositioning, institutional buyer appetite, timing optionality."),
            ("case_studies",             "Comparable Transactions",    "EVIDENCE",    "900-word analysis of 2-3 comparable {topic} transactions. Purchase price, CapEx, exit value, achieved IRR. What made them successful or not."),
            ("decision_framework",       "Investment Decision Framework","FRAMEWORK",  "900-word go/no-go decision framework. Minimum IRR hurdles, maximum CapEx per sq ft, market entry criteria, team capability requirements, deal structuring red lines."),
            ("performance_dashboard",    "KPI Dashboard",              "OUTCOMES",    "800-word financial KPI dashboard. 10+ metrics with target ranges. Monthly/quarterly monitoring cadence. Early warning indicators."),
            ("final_recommendations",    "Investment Recommendations", "CONCLUSION",  "600-word investment committee summary. Recommendation, key conditions, risk mitigants, next steps, and 90-day action plan."),
        ]
    },
    "trends_report": {
        "label": "Trends Report",
        "tone": "forward-looking, analytical, evidence-based",
        "structure_description": "15-page industry trends report with macro forces, technology shifts, regulatory evolution, and strategic implications",
        "sections": [
            ("executive_summary",        "Trends Executive Summary",   "OVERVIEW",    "700-word forward-looking executive brief. Top 5 trends reshaping {topic}. Why now. What {audience} must do in the next 12-24 months."),
            ("macro_forces",             "Macro Forces",               "MACRO",       "900-word analysis of macro forces driving change in {topic}. Economic, demographic, climate, geopolitical forces. Their specific impact on {industry}."),
            ("trend_1",                  "Trend 1: Technology",        "TREND",       "1000-word deep analysis of the primary technology trend in {topic}. Current adoption state, trajectory, leading adopters, laggard risk, investment requirements."),
            ("trend_2",                  "Trend 2: Regulatory",        "TREND",       "1000-word analysis of regulatory and policy evolution affecting {topic}. Current rules, upcoming changes, compliance timeline, strategic implications for {audience}."),
            ("trend_3",                  "Trend 3: Market Structure",  "TREND",       "1000-word analysis of structural market shifts in {topic}. Consolidation, new entrants, business model evolution, pricing pressure, demand shifts."),
            ("trend_4",                  "Trend 4: ESG & Sustainability","TREND",     "900-word analysis of ESG trends in {topic}. Net zero mandates, embodied carbon, social value requirements, green financing evolution, institutional requirements."),
            ("trend_5",                  "Trend 5: Workforce & Skills","TREND",       "900-word analysis of talent and capability trends in {topic}. Skills gaps, automation impact, workforce restructuring, training requirements."),
            ("early_adopter_analysis",   "Early Adopter Analysis",     "EVIDENCE",    "900-word analysis of organizations already leading on these trends. What they did, how early, what competitive advantage they gained."),
            ("laggard_risk",             "Laggard Risk Assessment",    "RISK",        "900-word analysis of the risk of not adapting. Financial penalties, market share erosion, regulatory non-compliance, talent drain, competitive displacement."),
            ("technology_roadmap",       "Technology Adoption Roadmap","ROADMAP",     "900-word technology adoption roadmap for {audience}. What to adopt now, what to pilot in 12 months, what to plan for in 24-36 months."),
            ("regulatory_strategy",      "Regulatory Strategy",        "STRATEGY",    "800-word regulatory anticipation strategy. How to stay ahead of incoming rules. Engagement strategies, compliance architecture, policy advocacy."),
            ("investment_implications",  "Investment Implications",    "FINANCIAL",   "900-word analysis of capital allocation implications of these trends. Where to invest, where to divest, emerging asset classes, stranded asset risk."),
            ("strategic_scenarios",      "Strategic Scenarios",        "SCENARIOS",   "900-word scenario planning. Three futures: accelerated transition, moderate adaptation, disruption/stagnation. Probability and strategic response for each."),
            ("action_framework",         "Action Framework",           "FRAMEWORK",   "800-word prioritized action framework for {audience}. Immediate actions (0-90 days), short-term agenda (90 days - 1 year), strategic priorities (1-3 years)."),
            ("final_recommendations",    "Strategic Imperatives",      "CONCLUSION",  "600-word closing imperatives. Top 5 actions ranked by urgency and impact. Who owns each. What success looks like in 24 months."),
        ]
    },
    "design_portfolio": {
        "label": "Design Portfolio",
        "tone": "creative, technical, portfolio-grade",
        "structure_description": "15-page professional design portfolio with project showcases, design philosophy, technical methodology, and client outcomes",
        "sections": [
            ("executive_summary",        "Studio Overview",            "STUDIO",      "700-word studio positioning statement. Design philosophy, core expertise in {topic}, types of clients served, signature approach to {pain_points}. Distinctive voice."),
            ("design_philosophy",        "Design Philosophy",          "PHILOSOPHY",  "900-word articulation of design philosophy specific to {topic}. Principles, influences, how the studio approaches the tension between {pain_points}. Substantive, not generic."),
            ("methodology",              "Design Methodology",         "METHOD",      "1000-word proprietary design methodology. Named process. Each phase: intent, tools, outputs, client touchpoints. Specific to {topic} projects."),
            ("project_1",                "Project Showcase: 1",        "PROJECT",     "1000-word detailed project case. Brief, design response, technical challenges, material choices, client outcomes. Specific measurements, timelines, costs where relevant."),
            ("project_2",                "Project Showcase: 2",        "PROJECT",     "1000-word detailed second project. Different typology or scale. Show range. Same depth: brief, response, technical resolution, outcome."),
            ("project_3",                "Project Showcase: 3",        "PROJECT",     "900-word third project showcase. Focus on innovation or a unique constraint overcome. What made this project advance the studio's thinking."),
            ("technical_expertise",      "Technical Expertise",        "TECHNICAL",   "900-word demonstration of technical depth in {topic}. Specific tools, software, structural knowledge, material science, environmental systems expertise."),
            ("sustainability_approach",  "Sustainability Approach",    "ESG",         "800-word sustainability methodology. How ESG is embedded in the design process for {topic}. Specific tools, certifications pursued, carbon performance achieved."),
            ("client_process",           "Client Engagement Process",  "PROCESS",     "800-word client-facing process. How the studio communicates, makes decisions, manages change, and delivers against brief. What clients experience."),
            ("innovation_research",      "Innovation & Research",      "INNOVATION",  "900-word section on R&D, innovation initiatives, academic partnerships, material research, and emerging design territories the studio is exploring in {topic}."),
            ("team_capability",          "Team & Capabilities",        "TEAM",        "800-word team structure and capability profile. Key roles, depth of experience, specialist consultants, technology stack, studio culture."),
            ("awards_recognition",       "Awards & Recognition",       "CREDENTIALS", "700-word curated list of awards, publications, peer recognition, and thought leadership contributions. Frame each in terms of what it validates about the studio's approach."),
            ("client_outcomes",          "Client Outcomes",            "OUTCOMES",    "900-word client outcome analysis. 3-4 client stories focused on the value delivered. Specific metrics: budget performance, timeline, tenant satisfaction, asset value uplift."),
            ("market_positioning",       "Market Positioning",         "POSITIONING", "800-word competitive positioning analysis. How the studio differs from the market, what it turns down, what it doubles down on. Value proposition for {audience}."),
            ("final_recommendations",    "Working With Us",            "ENGAGEMENT",  "600-word engagement overview. Typical project onboarding, fee structure approach, how to start. Ends with a clear, confident call to action."),
        ]
    },
    "client_onboarding": {
        "label": "Client Onboarding Flow",
        "tone": "clear, structured, client-facing",
        "structure_description": "15-page client onboarding document with process overview, expectation setting, decision frameworks, and collaboration protocols",
        "sections": [
            ("executive_summary",        "Welcome & Overview",         "WELCOME",     "700-word welcome document. What the client has engaged the firm to do, what success looks like, how this document helps them navigate the process. Warm but precise."),
            ("project_scope",            "Project Scope & Objectives", "SCOPE",       "900-word detailed scope statement specific to {topic}. What is included, what is explicitly excluded, key deliverables, success criteria, and how scope changes are managed."),
            ("team_introduction",        "Your Project Team",          "TEAM",        "800-word team introduction. Roles and responsibilities of each team member. Decision-making authority matrix. How to escalate. Communication protocols."),
            ("process_overview",         "Our Process",                "PROCESS",     "1000-word end-to-end process overview. All phases from briefing to handover. What happens in each phase, client inputs required, typical duration, key milestones."),
            ("phase_1_brief",            "Phase 1: Briefing",          "PHASE 1",     "900-word briefing phase guide. What the firm needs from the client. Brief document structure. How design intent is captured and verified. Sign-off process."),
            ("phase_2_design",           "Phase 2: Design Development","PHASE 2",     "900-word design development guide. How concepts are developed and presented. Revision rounds: what's included, what's additional. How decisions get locked in."),
            ("phase_3_approvals",        "Phase 3: Consents & Approvals","PHASE 3",   "800-word regulatory phase guide. What approvals are needed for {topic}. Timeline expectations. Client responsibilities vs firm responsibilities. Risk of delays."),
            ("phase_4_delivery",         "Phase 4: Construction",      "PHASE 4",     "900-word construction phase client guide. Site visits: frequency and protocol. How changes are managed. Progress reporting cadence. Payment milestone structure."),
            ("communication_protocol",   "Communication Protocols",    "COMMS",       "800-word communication framework. Meeting types and frequency. Document naming and storage. Email response SLAs. Emergency escalation path."),
            ("decision_framework",       "Decision-Making Framework",  "DECISIONS",   "800-word client decision guide. How to evaluate design options. What information the firm provides to support decisions. Timeframes for decisions. Consequence of delays."),
            ("change_management",        "Managing Changes",           "CHANGES",     "900-word change management protocol. How scope changes are identified, costed, and approved. What constitutes a variation. Change order process step by step."),
            ("risk_awareness",           "Key Risks to Understand",    "RISK",        "800-word honest risk briefing for the client. Top 8 risks on {topic} projects. What the firm does to mitigate them. What the client can do. What to do if one occurs."),
            ("financial_management",     "Financial Management",       "FINANCIAL",   "900-word client financial guide. Fee structure, payment milestones, invoice process, how contingency is managed, how to read a cost report."),
            ("quality_standards",        "Quality Standards",          "QUALITY",     "800-word quality framework. What the firm's quality standards are. How work is reviewed internally before client presentation. Defect resolution process."),
            ("final_recommendations",    "Getting the Best Outcome",   "CONCLUSION",  "600-word guide to being a great client. What great clients do differently. How to make good decisions under pressure. What the firm needs from the client to deliver excellence."),
        ]
    },
    "custom": {
        "label": "Custom Strategic Report",
        "tone": "authoritative, analytical, institutional",
        "structure_description": "15-page custom strategic report tailored entirely to the specified topic and audience",
        "sections": [
            ("executive_summary",        "Executive Summary",          "STRATEGY",    "800-word executive summary covering the full strategic landscape of {topic} for {audience}. Why this matters now, what the core challenges are, what this report delivers."),
            ("market_landscape",         "Market Landscape",           "MARKET",      "900-word market analysis. Current state of {topic}, key players, market dynamics, demand/supply forces, emerging patterns. No generic filler."),
            ("challenge_1",              "Core Challenge 1",           "ANALYSIS",    "1000-word analysis of the first critical challenge in {topic}. Derived directly from {pain_points}. Root causes, mechanisms, financial impact."),
            ("challenge_2",              "Core Challenge 2",           "ANALYSIS",    "1000-word analysis of the second critical challenge. Technical depth, real-world manifestation, quantified risk exposure."),
            ("challenge_3",              "Core Challenge 3",           "ANALYSIS",    "1000-word analysis of the third challenge specific to {pain_points}. Systemic causes, downstream effects, urgency drivers."),
            ("strategic_framework",      "Strategic Framework",        "FRAMEWORK",   "1000-word named proprietary framework for addressing {topic}. 4-5 pillars, each with 150-200 words. Feels like a real consulting methodology."),
            ("audience_application_1",   "Application for {audience} Group 1", "PLAYBOOK", "900-word section for the primary audience segment. Concrete implementation guidance, decision criteria, financial rationale."),
            ("audience_application_2",   "Application for {audience} Group 2", "PLAYBOOK", "900-word section for the secondary audience. Tailored steps, tools, coordination requirements."),
            ("risk_governance",          "Risk & Governance",          "RISK",        "900-word risk analysis. Risk matrix, contractual frameworks, contingency planning specific to {topic}."),
            ("financial_analysis",       "Financial Analysis",         "FINANCIAL",   "900-word financial modeling. Cost-benefit, IRR sensitivity, financing instruments, value creation levers for {topic}."),
            ("technology_tools",         "Technology & Tools",         "TECHNOLOGY",  "900-word section on technology solutions and tools relevant to {topic}. Current best-in-class, adoption barriers, implementation sequence."),
            ("case_studies",             "Case Studies",               "EVIDENCE",    "1000-word section with 2-3 case studies. Specific context, challenge, intervention, measurable outcome. Tied directly to {topic}."),
            ("implementation_roadmap",   "Implementation Roadmap",     "ROADMAP",     "900-word phased implementation roadmap. 4 phases with objectives, deliverables, timelines, and KPIs per phase."),
            ("performance_dashboard",    "Performance Dashboard",      "OUTCOMES",    "800-word KPI framework. 10 specific metrics with baseline targets, measurement method, monitoring frequency."),
            ("final_recommendations",    "Final Recommendations",      "CONCLUSION",  "600-word prioritized recommendations. Top 5 actions, 90-day quick wins, 12-month agenda, ROI forecast."),
        ]
    }
}


class GroqClient:
    """
    Groq-powered lead magnet generator.
    Supports 8 document types with deeply relevant, 15-page content.
    3 dynamic image placeholders keyed to: image_1_url, image_2_url, image_3_url
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        if not api_key:
            logger.error("❌ GROQ_API_KEY missing.")
            raise ValueError("GROQ_API_KEY is required.")

        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        self.temperature = 0.4   # Lower = more consistent, less hallucination
        self.max_tokens = 4096

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, Any]:
        topic        = user_answers.get("main_topic", "Strategic Design")
        audience     = user_answers.get("target_audience", "Stakeholders")
        pain_points  = user_answers.get("pain_points", [])
        doc_type     = user_answers.get("document_type", "guide").lower().replace(" ", "_")

        if isinstance(pain_points, list):
            pain_points_str = ", ".join(pain_points)
        else:
            pain_points_str = str(pain_points)

        # Normalise doc_type key
        type_map = {
            "guide": "guide",
            "case_study": "case_study",
            "checklist": "checklist",
            "roi_calculator": "roi_calculator",
            "trends_report": "trends_report",
            "design_portfolio": "design_portfolio",
            "client_onboarding_flow": "client_onboarding",
            "client_onboarding": "client_onboarding",
            "custom": "custom",
        }
        normalised_type = type_map.get(doc_type, "guide")

        return {
            "topic":        topic,
            "audience":     audience,
            "pain_points":  pain_points_str,
            "tone":         user_answers.get("tone", "Professional"),
            "industry":     user_answers.get("industry", "Architecture"),
            "document_type": normalised_type,
        }

    def generate_lead_magnet_json(self, signals: Dict[str, Any], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        doc_type = signals.get("document_type", "guide")
        config   = DOCUMENT_TYPE_CONFIGS.get(doc_type, DOCUMENT_TYPE_CONFIGS["guide"])

        logger.info(f"📄 Generating {config['label']} for topic: {signals['topic']}")

        # Build title first
        title_data = self._generate_title(signals, config, firm_profile)

        # Generate all 15 sections individually
        sections_content = {}
        for idx, (key, title, label, brief) in enumerate(config["sections"], 1):
            logger.info(f"✍️  Section {idx}/15: {key}")
            content = self._generate_section(
                key=key,
                title=title,
                label=label,
                brief=brief,
                signals=signals,
                config=config,
                firm_profile=firm_profile,
                section_num=idx,
            )
            sections_content[key] = content

        # Assign image placeholders to pages 4, 7, 11 (visual rhythm)
        image_assignments = {
            "image_1_page": list(config["sections"])[3][0],  # Section 4
            "image_2_page": list(config["sections"])[6][0],  # Section 7
            "image_3_page": list(config["sections"])[10][0], # Section 11
        }

        return {
            "title":                title_data.get("title", signals["topic"]),
            "subtitle":             title_data.get("subtitle", config["label"]),
            "target_audience_summary": title_data.get("target_audience_summary", ""),
            "document_type":        doc_type,
            "document_type_label":  config["label"],
            "sections_config":      config["sections"],
            "image_assignments":    image_assignments,
            "expansions":           sections_content,
        }

    def normalize_ai_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        exp    = raw.get("expansions", {})
        config = DOCUMENT_TYPE_CONFIGS.get(raw.get("document_type", "guide"), DOCUMENT_TYPE_CONFIGS["guide"])

        normalized = {
            "title":                 raw.get("title", "Strategic Report"),
            "subtitle":              raw.get("subtitle", ""),
            "summary":               raw.get("target_audience_summary", ""),
            "document_type":         raw.get("document_type", "guide"),
            "document_type_label":   raw.get("document_type_label", "Guide"),
            "sections_config":       config["sections"],
            "image_assignments":     raw.get("image_assignments", {}),
        }

        # Map every section key from config
        for key, title, label, _ in config["sections"]:
            normalized[key] = exp.get(key, "")

        # HTML safety
        for k, v in normalized.items():
            if isinstance(v, str) and "<" in v:
                normalized[k] = self._ensure_closed_tags(v)

        return normalized

    def map_to_template_vars(self, ai_content: Dict[str, Any], firm_profile: Dict[str, Any], signals: Dict[str, Any] = None) -> Dict[str, Any]:
        config = DOCUMENT_TYPE_CONFIGS.get(ai_content.get("document_type", "guide"), DOCUMENT_TYPE_CONFIGS["guide"])

        vars_ = {
            "mainTitle":              ai_content.get("title"),
            "documentSubtitle":       ai_content.get("subtitle"),
            "documentTypeLabel":      ai_content.get("document_type_label", "Guide"),
            "companyName":            firm_profile.get("firm_name"),
            "emailAddress":           firm_profile.get("work_email"),
            "phoneNumber":            firm_profile.get("phone_number"),
            "website":                firm_profile.get("firm_website"),
            "primaryColor":           firm_profile.get("primary_brand_color", "#2a5766"),
            "secondaryColor":         firm_profile.get("secondary_brand_color", "#FFFFFF"),
            "summary":                ai_content.get("summary"),
            "sections_config":        config["sections"],
            "image_assignments":      ai_content.get("image_assignments", {}),

            # Image URLs — passed from firm_profile or user uploads
            "image_1_url":            firm_profile.get("image_1_url", ""),
            "image_2_url":            firm_profile.get("image_2_url", ""),
            "image_3_url":            firm_profile.get("image_3_url", ""),
            "image_1_caption":        firm_profile.get("image_1_caption", "Strategic Context"),
            "image_2_caption":        firm_profile.get("image_2_caption", "Technical Framework"),
            "image_3_caption":        firm_profile.get("image_3_caption", "Implementation Overview"),

            "footerText":             f"© {firm_profile.get('firm_name', 'Strategic Report')}",
            "cta":                    ai_content.get("final_recommendations", "Contact us to implement this framework."),
        }

        # Map all section content keys
        for key, title, label, _ in config["sections"]:
            vars_[key]              = ai_content.get(key, "")
            vars_[f"{key}_title"]   = title
            vars_[f"{key}_label"]   = label

        return vars_

    def ensure_section_content(self, sections, signals, firm_profile):
        """Legacy compatibility method."""
        return sections or []

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE GENERATION METHODS
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_title(self, signals, config, firm_profile) -> Dict[str, Any]:
        system = "You are a senior document architect. Return valid JSON only. No markdown."
        prompt = f"""Generate a professional title package for this {config['label']}.

TOPIC: {signals['topic']}
AUDIENCE: {signals['audience']}
INDUSTRY: {signals['industry']}
PAIN POINTS: {signals['pain_points']}
DOCUMENT TYPE: {config['label']}
TONE: {config['tone']}

Return JSON:
{{
  "title": "Powerful 3-6 word institutional title, NO generic words like 'Ultimate' or 'Complete'",
  "subtitle": "12-15 word precise subtitle that names the specific value delivered",
  "target_audience_summary": "One sentence: who this is for and what specific outcome they get"
}}"""
        try:
            return self._call_ai(system, prompt)
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return {"title": signals["topic"], "subtitle": config["label"], "target_audience_summary": ""}

    def _generate_section(self, key: str, title: str, label: str, brief: str,
                          signals: Dict, config: Dict, firm_profile: Dict, section_num: int) -> str:
        """
        Generates a single section as HTML-ready prose.
        Brief is interpolated with topic/audience/pain_points for full relevance.
        """
        # Interpolate brief with actual values
        brief_filled = brief.format(
            topic=signals["topic"],
            audience=signals["audience"],
            pain_points=signals["pain_points"],
            industry=signals["industry"],
        )

        system = f"""You are a senior {signals['industry']} strategist writing a {config['label']}.
TONE: {config['tone']}
RULES:
- Write ONLY about {signals['topic']} as it applies to {signals['audience']}
- Every paragraph must address at least one of these pain points: {signals['pain_points']}
- Use specific metrics, percentages, and financial figures — no vague statements
- NO filler phrases like "it is important to note", "in today's world", "leveraging synergies"
- Write at institutional consulting grade — dense, analytical, specific
- Return valid JSON only. No markdown fences."""

        prompt = f"""Write Section {section_num} of 15 for this {config['label']}.

SECTION TITLE: {title}
CONTENT BRIEF: {brief_filled}

STRICT REQUIREMENTS:
- Minimum word count: see brief (800-1000 words for analysis sections, 600-700 for summary sections)
- Must be ENTIRELY about {signals['topic']} — no generic industry filler
- Must name specific challenges from: {signals['pain_points']}
- Include at least 3 specific metrics or data points
- Write in flowing prose — not bullet lists (unless the document type is a checklist)
- HTML is allowed: use <strong> for emphasis, <br> for line breaks where needed

Return JSON: {{ "{key}": "full HTML-ready prose content here" }}"""

        try:
            result = self._call_ai(system, prompt)
            content = result.get(key, "")
            if not content or len(content.split()) < 100:
                raise ValueError(f"Section {key} too short: {len(content.split())} words")
            return content
        except Exception as e:
            logger.error(f"❌ Section {key} failed: {e}. Retrying with simplified prompt...")
            return self._retry_section(key, title, signals, config)

    def _retry_section(self, key: str, title: str, signals: Dict, config: Dict) -> str:
        """Simplified retry for failed sections."""
        prompt = f"""Write 600 words about "{title}" specifically for {signals['topic']} addressing {signals['pain_points']} for {signals['audience']} in {signals['industry']}. Return JSON: {{"{key}": "prose"}}"""
        try:
            result = self._call_ai("You are a senior strategist. Return JSON only.", prompt)
            return result.get(key, f"Strategic analysis of {title} for {signals['topic']}.")
        except Exception:
            return f"<strong>{title}</strong><br>Strategic analysis of {signals['topic']} as it relates to {signals['pain_points']} for {signals['audience']}."

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Dict[str, Any]:
        est = self._estimate_tokens(system_prompt + user_prompt)
        logger.info(f"📡 Groq call | est_input_tokens={est}")

        start = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            response_format={"type": "json_object"},
        )
        duration = time.time() - start

        raw = response.choices[0].message.content
        logger.info(f"✅ Groq response | duration={duration:.2f}s | finish={response.choices[0].finish_reason}")

        if response.choices[0].finish_reason == "length":
            raise ValueError("Groq response truncated — max_tokens reached")

        return json.loads(raw)

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────────────────────────────

    def _estimate_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3) if text else 0

    def _ensure_closed_tags(self, html: str) -> str:
        if not html:
            return html
        void_tags = {"br", "hr", "img", "input", "link", "meta"}
        tags = re.findall(r"<(/?)([a-zA-Z1-6]+)", html)
        stack = []
        for is_closing, tag in tags:
            tag = tag.lower()
            if tag in void_tags:
                continue
            if is_closing:
                if stack and stack[-1] == tag:
                    stack.pop()
            else:
                stack.append(tag)
        for tag in reversed(stack):
            html += f"</{tag}>"
        return html
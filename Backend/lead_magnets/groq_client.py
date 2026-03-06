import os
import json
import logging
import time
import re
from typing import Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT TYPE CONFIGURATIONS
# ─────────────────────────────────────────────────────────────────────────────
DOCUMENT_TYPE_CONFIGS = {
    "guide": {
        "label": "Strategic Guide",
        "tone": "authoritative, analytical, institutional",
        "sections": [
            ("executive_summary",      "Executive Summary",               "STRATEGY",   "800-word executive-level overview of {topic} for {audience}. What the problem is, why it matters now, what this guide delivers. Include ROI context and strategic urgency specific to {pain_points}. No filler sentences."),
            ("market_landscape",       "Market Landscape",                "MARKET",     "900-word analysis of the current state of {topic} in {industry}. Include market pressures, emerging shifts, and why {audience} must act now. Reference real market dynamics tied to {pain_points}."),
            ("core_challenge_1",       "Core Challenge: Complexity",      "ANALYSIS",   "1000-word deep technical analysis of the first major challenge in {topic} for {audience}. Root causes, mechanisms, financial and operational impact of {pain_points}. Data-driven specifics only."),
            ("core_challenge_2",       "Core Challenge: Alignment",       "ANALYSIS",   "1000-word deep technical analysis of the second major challenge specific to {pain_points}. Quantified risk exposure, failure modes, and downstream consequences for {audience}."),
            ("core_challenge_3",       "Core Challenge: Risk",            "ANALYSIS",   "1000-word analysis of the third challenge in {topic}. Focus on systemic causes, timeline risk, and financial exposure for {audience} dealing with {pain_points}."),
            ("strategic_framework",    "Strategic Framework",             "FRAMEWORK",  "1000-word proprietary named framework for solving {topic}. Define 4 pillars. Each pillar gets 200 words of substance. Tie every pillar to {pain_points} and {audience} needs."),
            ("audience_playbook_1",    "Commercial Stakeholder Playbook", "PLAYBOOK",   "800-word section for commercial and institutional stakeholders in {audience}. Concrete decision criteria, financial logic, and implementation steps specific to {topic}."),
            ("audience_playbook_2",    "Technical Practitioner Playbook", "PLAYBOOK",   "800-word section for technical practitioners. Implementation steps, coordination protocols, and tools for {topic} addressing {pain_points}."),
            ("audience_playbook_3",    "Public Sector Playbook",          "PLAYBOOK",   "800-word section for government and regulatory audiences. Policy levers, approval acceleration, ESG alignment for {topic}."),
            ("risk_governance",        "Risk and Governance",             "RISK",       "900-word risk allocation, contractual frameworks, contingency planning specific to {topic} for {audience}. Include a risk matrix with 6 specific risks from {pain_points}."),
            ("financial_modeling",     "Financial Modeling",              "FINANCIAL",  "900-word IRR analysis, CapEx sensitivity, cost-benefit modeling, and financing instruments relevant to {topic} for {audience}. Specific numbers and ranges."),
            ("case_studies",           "Case Studies",                    "EVIDENCE",   "1000-word section with 2 detailed case studies directly about {topic}. Each: context, challenge from {pain_points}, intervention, measurable outcome with specific numbers."),
            ("implementation_roadmap", "Implementation Roadmap",          "ROADMAP",    "900-word phased roadmap for {audience} implementing {topic} solutions. Phase 1: Discovery (weeks 1-4). Phase 2: Design (weeks 5-10). Phase 3: Execution (weeks 11-24). Phase 4: Optimization. Each phase: objectives, deliverables, KPIs."),
            ("performance_dashboard",  "Performance Dashboard",           "OUTCOMES",   "800-word KPI framework for {topic}. 8 specific metrics with before/after targets, measurement methodology, and monitoring cadence. Tied directly to {pain_points} resolution."),
            ("final_recommendations",  "Final Recommendations",           "CONCLUSION", "600-word authoritative conclusion. Top 5 prioritized recommendations for {audience} on {topic}. 90-day quick wins, 12-month agenda, ROI forecast."),
        ]
    },
    "case_study": {
        "label": "Case Study Report",
        "tone": "evidence-based, precise, outcome-focused",
        "sections": [
            ("executive_summary",      "Executive Summary",               "OVERVIEW",     "700-word executive brief: project type related to {topic}, core challenges from {pain_points}, methodology, headline outcomes for {audience}."),
            ("project_context",        "Project Context",                 "CONTEXT",      "900-word detailed project background for {topic}. Asset type, strategic objectives, baseline conditions, constraints. Specific and grounded in {industry}."),
            ("challenge_diagnosis",    "Challenge Diagnosis",             "CHALLENGE",    "1000-word forensic analysis of problems faced. Root cause mapping of {pain_points}, failure point identification, risk exposure. Technical and financial dimensions for {audience}."),
            ("stakeholder_landscape",  "Stakeholder Landscape",           "STAKEHOLDERS", "800-word mapping of all stakeholders relevant to {topic}. How misalignment from {pain_points} manifested. What was at stake for each party in {audience}."),
            ("methodology_overview",   "Intervention Methodology",        "METHOD",       "1000-word description of the strategic approach taken for {topic}. Why this methodology over alternatives. Logic of each decision relative to {pain_points}."),
            ("phase_1_execution",      "Phase 1: Discovery",              "EXECUTION",    "900-word account of Phase 1 for {topic} project. What was found, what was unexpected, how team responded. Specific findings with numbers tied to {pain_points}."),
            ("phase_2_execution",      "Phase 2: Design and Planning",    "EXECUTION",    "900-word account of Phase 2. Design decisions, coordination mechanisms, approval strategy for {topic} addressing {pain_points}."),
            ("phase_3_execution",      "Phase 3: Delivery",               "EXECUTION",    "900-word account of delivery phase for {topic}. Trade sequencing, issue resolution, quality milestones. Specific to {audience}."),
            ("risk_events",            "Risk Events and Responses",       "RISK",         "800-word section on specific risk events from {pain_points}. How each was identified, escalated, and resolved for {topic}. Contractual mechanisms used."),
            ("financial_performance",  "Financial Performance",           "FINANCIAL",    "900-word financial analysis of {topic} project. Budget vs actuals, change order volume, IRR achieved vs target, CapEx efficiency for {audience}."),
            ("esg_outcomes",           "ESG and Social Outcomes",         "ESG",          "800-word environmental, social, and governance outcomes from {topic}. Carbon savings, community impact, regulatory compliance for {audience}."),
            ("lessons_learned",        "Lessons Learned",                 "INSIGHTS",     "900-word honest debrief on {topic}. What worked, what did not, what to do differently. Actionable insights tied to {pain_points} for {audience}."),
            ("replication_framework",  "Replication Framework",           "FRAMEWORK",    "900-word guide on replicating {topic} success for {audience}. Prerequisites, decision criteria, team structure, timeline expectations."),
            ("performance_dashboard",  "Performance Dashboard",           "OUTCOMES",     "800-word KPI summary for {topic}. 10 metrics with baseline vs outcome. Tied directly to {pain_points} resolution."),
            ("final_recommendations",  "Strategic Recommendations",       "CONCLUSION",   "600-word conclusion for {audience} considering {topic} projects. Top 5 recommendations with rationale and risk-adjusted ROI estimate."),
        ]
    },
    "checklist": {
        "label": "Implementation Checklist",
        "tone": "precise, actionable, practitioner-grade",
        "sections": [
            ("executive_summary",      "How to Use This Checklist",       "OVERVIEW",   "700-word guide on using this checklist for {topic}. Who in {audience} should use it, when, in what sequence. How to handle incomplete items tied to {pain_points}."),
            ("pre_project_checklist",  "Pre-Project Verification",        "PHASE 0",    "900-word pre-project checklist for {topic}. 15 specific verification items across mandate clarity, budget approval, team assembly, site due diligence. Each item 2-3 sentences for {audience}."),
            ("site_assessment",        "Site and Technical Assessment",   "PHASE 1",    "900-word site assessment checklist for {topic}. Structural surveys, condition audits, constraint mapping specific to {pain_points}. Pass/fail criteria for {audience}."),
            ("design_checklist",       "Design and Documentation",        "PHASE 2",    "900-word design phase checklist for {topic}. Documentation requirements, coordination meetings, consultant appointments, submission items specific to {industry}."),
            ("procurement_checklist",  "Procurement and Contracting",     "PHASE 3",    "900-word procurement checklist for {topic}. Tender documents, contractor selection criteria, contract form selection, insurance requirements tied to {pain_points}."),
            ("approval_checklist",     "Regulatory Approvals",            "APPROVALS",  "900-word approvals checklist for {topic} in {industry}. Each approval with responsible party, typical timeline, and common blockers from {pain_points}."),
            ("mobilisation_checklist", "Site Mobilisation",               "PHASE 4",    "800-word pre-construction mobilisation checklist for {topic}. Site establishment, safety plan, logistics plan specific to {audience} needs."),
            ("early_works_checklist",  "Early Works Execution",           "PHASE 5",    "900-word early works checklist for {topic}. Phased execution steps, hold points and sign-off requirements. Addresses {pain_points} at source."),
            ("main_works_checklist",   "Main Works Execution",            "PHASE 6",    "900-word main works checklist for {topic} by trade or workstream. Inspection hold points. Coordination items. Specific to {industry} and {audience}."),
            ("quality_checklist",      "Quality Assurance Gates",         "QA/QC",      "800-word QA checklist for {topic}. Inspection and test plan items, defect management, third-party verification requirements for {audience}."),
            ("risk_register",          "Risk Register Checklist",         "RISK",       "900-word risk management checklist for {topic}. 15 specific risks from {pain_points} with likelihood, impact, mitigation, and monitoring frequency."),
            ("handover_checklist",     "Practical Completion",            "PHASE 7",    "900-word handover checklist for {topic}. Defects inspection, documentation, commissioning certificates, training completion for {audience}."),
            ("post_occupancy",         "Post-Occupancy Review",           "PHASE 8",    "800-word post-occupancy checklist for {topic}. Review items at 6 weeks and 6 months. Performance checks tied to {pain_points} resolution."),
            ("compliance_tracker",     "Compliance and Reporting",        "COMPLIANCE", "800-word ongoing compliance checklist for {topic} in {industry}. Conditions discharge, ESG reporting, insurance renewals for {audience}."),
            ("final_recommendations",  "Checklist Master Summary",        "SUMMARY",    "600-word master summary for {topic}. Critical path items, most commonly missed items, decision gate summary for {audience} dealing with {pain_points}."),
        ]
    },
    "roi_calculator": {
        "label": "ROI Analysis Report",
        "tone": "financial, quantitative, investment-grade",
        "sections": [
            ("executive_summary",      "Investment Summary",              "OVERVIEW",   "700-word investment-grade executive summary for {topic}. Headline ROI metrics, investment thesis, key assumptions, risk-adjusted return range for {audience}."),
            ("market_opportunity",     "Market Opportunity",              "MARKET",     "900-word market sizing for {topic} in {industry}. Demand drivers, supply constraints, pricing dynamics tied to {pain_points}. Entry timing rationale for {audience}."),
            ("baseline_financials",    "Baseline Financial Model",        "FINANCIALS", "1000-word baseline financial model for {topic}. Revenue assumptions, cost structure, CapEx requirements, operating cost projections specific to {audience}."),
            ("roi_calculation",        "ROI Calculation Methodology",     "ROI",        "1000-word ROI calculation for {topic}. IRR, NPV, payback period, cash-on-cash return. Step-by-step with assumptions addressing {pain_points}."),
            ("capex_analysis",         "CapEx Deep Dive",                 "CAPEX",      "900-word CapEx analysis for {topic}. Hard costs, soft costs, contingency specific to {industry} and {pain_points} for {audience}."),
            ("revenue_modeling",       "Revenue and NOI Modeling",        "REVENUE",    "900-word revenue model for {topic}. Rate assumptions, occupancy projections, lease structure tied to {pain_points}. NOI build-up for {audience}."),
            ("sensitivity_analysis",   "Sensitivity Analysis",            "RISK",       "1000-word sensitivity analysis for {topic}. IRR sensitivity to key variables from {pain_points}. Conservative/base/optimistic cases for {audience}."),
            ("financing_structure",    "Financing Structure",             "FINANCING",  "900-word financing analysis for {topic}. Debt vs equity split, green bond eligibility, tax credit opportunities specific to {industry}."),
            ("risk_adjusted_returns",  "Risk-Adjusted Returns",           "RISK",       "900-word risk-adjusted analysis for {topic}. Probability-weighted IRR. Downside protection tied to {pain_points} for {audience}."),
            ("esg_value",              "ESG Value Premium",               "ESG",        "800-word ESG financial value for {topic}. Green premium, lower financing costs, carbon credit value specific to {industry} and {audience}."),
            ("exit_strategy",          "Exit Strategy Analysis",          "EXIT",       "900-word exit analysis for {topic}. Hold vs sell framework, exit cap rate assumptions tied to {pain_points}. Buyer appetite in {industry}."),
            ("case_studies",           "Comparable Transactions",         "EVIDENCE",   "900-word analysis of 2-3 comparable {topic} transactions. Achieved IRR, CapEx, exit value. What made them succeed relative to {pain_points}."),
            ("decision_framework",     "Investment Decision Framework",   "FRAMEWORK",  "900-word go/no-go decision framework for {topic}. Minimum hurdles, entry criteria, deal structuring red lines for {audience} in {industry}."),
            ("performance_dashboard",  "KPI Dashboard",                   "OUTCOMES",   "800-word financial KPI dashboard for {topic}. 10 metrics with target ranges. Early warning indicators tied to {pain_points} for {audience}."),
            ("final_recommendations",  "Investment Recommendations",      "CONCLUSION", "600-word investment committee summary for {topic}. Recommendation, key conditions, risk mitigants, next steps for {audience}."),
        ]
    },
    "trends_report": {
        "label": "Trends Report",
        "tone": "forward-looking, analytical, evidence-based",
        "sections": [
            ("executive_summary",       "Trends Executive Summary",        "OVERVIEW",   "700-word forward-looking executive brief on {topic}. Top 5 trends. Why now. What {audience} must do in the next 12-24 months given {pain_points}."),
            ("macro_forces",            "Macro Forces",                    "MACRO",      "900-word macro forces driving change in {topic} for {audience}. Economic, demographic, climate, geopolitical forces specific to {industry} and {pain_points}."),
            ("trend_1",                 "Trend 1: Technology Shift",       "TREND",      "1000-word deep analysis of the primary technology trend in {topic}. Current adoption state, trajectory, investment requirements for {audience} addressing {pain_points}."),
            ("trend_2",                 "Trend 2: Regulatory Evolution",   "TREND",      "1000-word analysis of regulatory and policy evolution in {topic} for {industry}. Upcoming changes, compliance timeline, strategic implications for {audience}."),
            ("trend_3",                 "Trend 3: Market Structure",       "TREND",      "1000-word structural market shifts in {topic}. Business model evolution, demand shifts, pricing pressure tied to {pain_points} for {audience}."),
            ("trend_4",                 "Trend 4: ESG Acceleration",       "TREND",      "900-word ESG trends in {topic} for {industry}. Net zero mandates, social value requirements, green financing evolution for {audience}."),
            ("trend_5",                 "Trend 5: Workforce and Skills",   "TREND",      "900-word talent and capability trends in {topic}. Skills gaps, automation impact specific to {pain_points} and {audience}."),
            ("early_adopter_analysis",  "Early Adopter Analysis",          "EVIDENCE",   "900-word analysis of organizations leading on {topic} trends. What competitive advantage they gained relevant to {audience} and {pain_points}."),
            ("laggard_risk",            "Laggard Risk Assessment",         "RISK",       "900-word risk of not adapting to {topic} trends. Financial penalties, market share erosion, regulatory non-compliance for {audience} with {pain_points}."),
            ("technology_roadmap",      "Technology Adoption Roadmap",     "ROADMAP",    "900-word technology adoption roadmap for {audience} in {topic}. What to adopt now, what to pilot in 12 months, what to plan for in 24-36 months."),
            ("regulatory_strategy",     "Regulatory Strategy",             "STRATEGY",   "800-word regulatory anticipation strategy for {topic} in {industry}. How {audience} stays ahead of incoming rules tied to {pain_points}."),
            ("investment_implications", "Investment Implications",          "FINANCIAL",  "900-word capital allocation implications of {topic} trends for {audience}. Where to invest, where to divest, stranded asset risk from {pain_points}."),
            ("strategic_scenarios",     "Strategic Scenarios",             "SCENARIOS",  "900-word scenario planning for {topic}. Three futures. Probability and strategic response for {audience} dealing with {pain_points}."),
            ("action_framework",        "Action Framework",                "FRAMEWORK",  "800-word prioritized action framework for {audience} on {topic}. Immediate (0-90 days), short-term (90 days-1 year), strategic (1-3 years)."),
            ("final_recommendations",   "Strategic Imperatives",           "CONCLUSION", "600-word closing imperatives for {audience} on {topic}. Top 5 actions ranked by urgency. What success looks like in 24 months given {pain_points}."),
        ]
    },
    "design_portfolio": {
        "label": "Design Portfolio",
        "tone": "creative, technical, portfolio-grade",
        "sections": [
            ("executive_summary",       "Studio Overview",                 "STUDIO",      "700-word studio positioning for {topic}. Design philosophy, core expertise, signature approach to {pain_points} for {audience}."),
            ("design_philosophy",       "Design Philosophy",               "PHILOSOPHY",  "900-word design philosophy specific to {topic}. Principles, how the studio approaches {pain_points} for {audience} in {industry}."),
            ("methodology",             "Design Methodology",              "METHOD",      "1000-word proprietary design methodology for {topic}. Named process with phases, tools, outputs, client touchpoints. Specific to {pain_points}."),
            ("project_1",               "Project Showcase One",            "PROJECT",     "1000-word detailed project case for {topic}. Brief, design response to {pain_points}, technical challenges, outcomes for {audience}."),
            ("project_2",               "Project Showcase Two",            "PROJECT",     "1000-word second project for {topic}. Different typology. Show range. Brief, response to {pain_points}, technical resolution, outcome."),
            ("project_3",               "Project Showcase Three",          "PROJECT",     "900-word third project for {topic}. Focus on innovation in addressing {pain_points} for {audience} in {industry}."),
            ("technical_expertise",     "Technical Expertise",             "TECHNICAL",   "900-word technical depth in {topic}. Specific tools, software, material science knowledge addressing {pain_points}."),
            ("sustainability_approach", "Sustainability Approach",         "ESG",         "800-word sustainability methodology for {topic} in {industry}. ESG tools, certifications, carbon performance for {audience}."),
            ("client_process",          "Client Engagement Process",       "PROCESS",     "800-word client-facing process for {topic}. How decisions get made, changes managed, brief delivered for {audience}."),
            ("innovation_research",     "Innovation and Research",         "INNOVATION",  "900-word R&D initiatives in {topic}. Emerging design territories addressing {pain_points} for {audience}."),
            ("team_capability",         "Team and Capabilities",           "TEAM",        "800-word team structure and capability for {topic}. Key roles, specialist expertise, technology stack for {industry}."),
            ("awards_recognition",      "Awards and Recognition",          "CREDENTIALS", "700-word curated recognition for {topic} work. What each award validates about the approach to {pain_points}."),
            ("client_outcomes",         "Client Outcomes",                 "OUTCOMES",    "900-word client outcome analysis for {topic}. 3-4 stories focused on value delivered against {pain_points} for {audience}."),
            ("market_positioning",      "Market Positioning",              "POSITIONING", "800-word competitive positioning for {topic}. How the studio differs from the market on {pain_points} for {audience}."),
            ("final_recommendations",   "Working With Us",                 "ENGAGEMENT",  "600-word engagement overview for {topic}. Onboarding, fee approach, how to start. Clear call to action for {audience}."),
        ]
    },
    "client_onboarding": {
        "label": "Client Onboarding Flow",
        "tone": "clear, structured, client-facing",
        "sections": [
            ("executive_summary",      "Welcome and Overview",            "WELCOME",    "700-word welcome for {topic} engagement. What success looks like, how this document helps {audience} navigate {pain_points}."),
            ("project_scope",          "Project Scope and Objectives",    "SCOPE",      "900-word scope statement for {topic}. What is included, excluded, key deliverables, success criteria, how {pain_points} are managed."),
            ("team_introduction",      "Your Project Team",               "TEAM",       "800-word team introduction for {topic}. Roles, responsibilities, decision-making authority. How to escalate {pain_points}."),
            ("process_overview",       "Our Process",                     "PROCESS",    "1000-word end-to-end process for {topic}. All phases from briefing to handover. What {audience} inputs are required."),
            ("phase_1_brief",          "Phase 1: Briefing",               "PHASE 1",    "900-word briefing phase guide for {topic}. What is needed from {audience}. How {pain_points} are captured and addressed."),
            ("phase_2_design",         "Phase 2: Design Development",     "PHASE 2",    "900-word design development guide for {topic}. How concepts address {pain_points}. Revision rounds for {audience}."),
            ("phase_3_approvals",      "Phase 3: Consents and Approvals", "PHASE 3",    "800-word regulatory phase guide for {topic} in {industry}. What approvals are needed. Timeline expectations for {audience}."),
            ("phase_4_delivery",       "Phase 4: Construction",           "PHASE 4",    "900-word construction phase guide for {topic}. How {pain_points} are managed. Progress reporting for {audience}."),
            ("communication_protocol", "Communication Protocols",         "COMMS",      "800-word communication framework for {topic}. Meeting types, document standards, SLAs, escalation for {pain_points}."),
            ("decision_framework",     "Decision-Making Framework",       "DECISIONS",  "800-word client decision guide for {topic}. How to evaluate options tied to {pain_points}. Consequence of delays for {audience}."),
            ("change_management",      "Managing Changes",                "CHANGES",    "900-word change management protocol for {topic}. How scope changes from {pain_points} are identified, costed, approved."),
            ("risk_awareness",         "Key Risks to Understand",         "RISK",       "800-word risk briefing for {audience} on {topic}. Top 8 risks from {pain_points}. What the firm does and what the client can do."),
            ("financial_management",   "Financial Management",            "FINANCIAL",  "900-word financial guide for {audience} on {topic}. Fee structure, payment milestones, how {pain_points} affect costs."),
            ("quality_standards",      "Quality Standards",               "QUALITY",    "800-word quality framework for {topic}. Standards, internal review, defect resolution for {audience} and {pain_points}."),
            ("final_recommendations",  "Getting the Best Outcome",        "CONCLUSION", "600-word guide for {audience} on {topic}. What great clients do differently when facing {pain_points}."),
        ]
    },
    "custom": {
        "label": "Custom Strategic Report",
        "tone": "authoritative, analytical, institutional",
        "sections": [
            ("executive_summary",      "Executive Summary",               "STRATEGY",   "800-word executive summary of {topic} for {audience}. Why {pain_points} matter now, what this report delivers."),
            ("market_landscape",       "Market Landscape",                "MARKET",     "900-word market analysis of {topic} in {industry}. Key dynamics, demand/supply forces, patterns relevant to {pain_points} and {audience}."),
            ("challenge_1",            "Core Challenge One",              "ANALYSIS",   "1000-word analysis of the first critical challenge in {topic}. Root causes, mechanisms, financial impact of {pain_points} on {audience}."),
            ("challenge_2",            "Core Challenge Two",              "ANALYSIS",   "1000-word analysis of the second critical challenge in {topic}. Technical depth, quantified risk exposure from {pain_points} for {audience}."),
            ("challenge_3",            "Core Challenge Three",            "ANALYSIS",   "1000-word analysis of the third challenge in {topic} specific to {pain_points}. Systemic causes, urgency drivers for {audience}."),
            ("strategic_framework",    "Strategic Framework",             "FRAMEWORK",  "1000-word named framework for {topic}. 4 pillars each tied to {pain_points}. Real consulting methodology for {audience} in {industry}."),
            ("audience_application_1", "Application: Group One",          "PLAYBOOK",   "900-word section for the primary {audience} segment on {topic}. Concrete implementation guidance for {pain_points}."),
            ("audience_application_2", "Application: Group Two",          "PLAYBOOK",   "900-word section for the secondary {audience} on {topic}. Tailored steps, tools, coordination for {pain_points}."),
            ("risk_governance",        "Risk and Governance",             "RISK",       "900-word risk analysis for {topic}. Risk matrix, contractual frameworks, contingency specific to {pain_points} for {audience}."),
            ("financial_analysis",     "Financial Analysis",              "FINANCIAL",  "900-word financial modeling for {topic}. Cost-benefit, IRR sensitivity, financing for {audience} addressing {pain_points}."),
            ("technology_tools",       "Technology and Tools",            "TECHNOLOGY", "900-word technology solutions for {topic}. Best-in-class tools, adoption barriers, implementation sequence for {pain_points}."),
            ("case_studies",           "Case Studies",                    "EVIDENCE",   "1000-word section with 2-3 case studies on {topic}. Specific context, challenge from {pain_points}, measurable outcome for {audience}."),
            ("implementation_roadmap", "Implementation Roadmap",          "ROADMAP",    "900-word phased roadmap for {audience} on {topic}. 4 phases with objectives, deliverables, KPIs tied to {pain_points}."),
            ("performance_dashboard",  "Performance Dashboard",           "OUTCOMES",   "800-word KPI framework for {topic}. 10 metrics with baseline targets tied to {pain_points} for {audience}."),
            ("final_recommendations",  "Final Recommendations",           "CONCLUSION", "600-word prioritized recommendations for {audience} on {topic}. Top 5 actions, 90-day wins, ROI forecast for {pain_points}."),
        ]
    }
}

# Frontend value → config key normalisation
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


class GroqClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")
        self.client      = Groq(api_key=api_key)
        self.model       = "llama-3.3-70b-versatile"
        self.temperature = 0.4
        self.max_tokens  = 4096

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, Any]:
        raw_type = str(
            user_answers.get("document_type")
            or user_answers.get("lead_magnet_type")
            or "guide"
        ).lower().strip()

        doc_type    = _TYPE_MAP.get(raw_type, "guide")
        pain_points = user_answers.get("pain_points", [])

        return {
            "topic":         user_answers.get("main_topic", "Strategic Design"),
            "audience":      user_answers.get("target_audience", "Stakeholders"),
            "pain_points":   ", ".join(pain_points) if isinstance(pain_points, list) else str(pain_points),
            "tone":          user_answers.get("tone", "Professional"),
            "industry":      user_answers.get("industry", "Architecture"),
            "document_type": doc_type,
        }

    def generate_lead_magnet_json(self, signals: Dict[str, Any], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        doc_type = signals.get("document_type", "guide")
        config   = DOCUMENT_TYPE_CONFIGS.get(doc_type, DOCUMENT_TYPE_CONFIGS["guide"])

        logger.info(f"📄 Generating {config['label']} | topic={signals['topic']}")

        title_data        = self._generate_title(signals, config)
        sections_content: Dict[str, str] = {}

        for idx, (key, title, label, brief) in enumerate(config["sections"], 1):
            logger.info(f"✍️  Section {idx}/15: {key}")
            sections_content[key] = self._generate_section(
                key=key, title=title, label=label, brief=brief,
                signals=signals, config=config, section_num=idx,
            )

        return {
            "title":                   title_data.get("title", signals["topic"]),
            "subtitle":                title_data.get("subtitle", config["label"]),
            "target_audience_summary": title_data.get("target_audience_summary", ""),
            "document_type":           doc_type,
            "document_type_label":     config["label"],
            "expansions":              sections_content,
        }

    def normalize_ai_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        exp      = raw.get("expansions", {})
        doc_type = raw.get("document_type", "guide")
        config   = DOCUMENT_TYPE_CONFIGS.get(doc_type, DOCUMENT_TYPE_CONFIGS["guide"])

        normalized: Dict[str, Any] = {
            "title":               raw.get("title", "Strategic Report"),
            "subtitle":            raw.get("subtitle", ""),
            "summary":             raw.get("target_audience_summary", ""),
            "document_type":       doc_type,
            "document_type_label": raw.get("document_type_label", config["label"]),
            "sections_config":     config["sections"],
        }

        for key, _title, _label, _ in config["sections"]:
            content = exp.get(key, "")
            if isinstance(content, dict):
                content = json.dumps(content)
            normalized[key] = content if isinstance(content, str) else str(content)

        for k, v in normalized.items():
            if isinstance(v, str) and "<" in v:
                normalized[k] = self._ensure_closed_tags(v)

        return normalized

    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Dict[str, Any],
        signals: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Builds the flat dict Jinja2 Template.html receives.
        KEY FIX: `content_sections` and `toc_sections` are plain Python lists
        of dicts so the template can loop with {% for section in content_sections %}
        without needing vars() or any Python introspection.
        """
        doc_type     = ai_content.get("document_type", "guide")
        config       = DOCUMENT_TYPE_CONFIGS.get(doc_type, DOCUMENT_TYPE_CONFIGS["guide"])
        sections_cfg = config["sections"]

        content_sections: List[Dict] = []
        toc_sections:     List[Dict] = []
        fallback_caps     = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        for idx, (key, title, label, _) in enumerate(sections_cfg):
            page_num = f"{idx + 3:02d}"
            content  = ai_content.get(key, "")
            first_alpha = next(
                (c for c in (content or "") if c.isalpha()),
                fallback_caps[idx % 26],
            )
            content_sections.append({
                "key":      key,
                "title":    title,
                "label":    label,
                "page_num": page_num,
                "content":  content,
                "drop_cap": first_alpha.upper(),
            })
            toc_sections.append({
                "title":    title,
                "label":    label,
                "page_num": page_num,
            })

        primary_color = (
            firm_profile.get("primary_brand_color")
            or (signals or {}).get("primary_color")
            or "#2a5766"
        )
        if primary_color and not str(primary_color).startswith("#"):
            primary_color = "#" + primary_color

        vars_: Dict[str, Any] = {
            "mainTitle":         ai_content.get("title"),
            "documentSubtitle":  ai_content.get("subtitle"),
            "documentTypeLabel": ai_content.get("document_type_label", config["label"]),
            "companyName":       firm_profile.get("firm_name", ""),
            "emailAddress":      firm_profile.get("work_email", ""),
            "phoneNumber":       firm_profile.get("phone_number", ""),
            "website":           firm_profile.get("firm_website", ""),
            "footerText":        f"© {firm_profile.get('firm_name', 'Strategic Report')}",
            "primaryColor":      primary_color,
            "secondaryColor":    firm_profile.get("secondary_brand_color") or "#FFFFFF",
            "summary":           ai_content.get("summary", ""),

            # THE KEY FIX — template loops over these directly
            "content_sections":  content_sections,
            "toc_sections":      toc_sections,

            # Images
            "image_1_url":       firm_profile.get("image_1_url", ""),
            "image_2_url":       firm_profile.get("image_2_url", ""),
            "image_3_url":       firm_profile.get("image_3_url", ""),
            "image_1_caption":   firm_profile.get("image_1_caption", "Strategic Context"),
            "image_2_caption":   firm_profile.get("image_2_caption", "Technical Framework"),
            "image_3_caption":   firm_profile.get("image_3_caption", "Implementation Overview"),

            "cta": ai_content.get("final_recommendations", "Contact us to implement this framework."),
        }

        # Also expose flat keys for any legacy template references
        for key, _title, _label, _ in sections_cfg:
            vars_[key] = ai_content.get(key, "")

        return vars_

    def ensure_section_content(self, sections, signals, firm_profile):
        """Legacy compatibility."""
        return sections or []

    # ── PRIVATE GENERATION ────────────────────────────────────────────────────

    def _generate_title(self, signals: Dict, config: Dict) -> Dict:
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
  "title": "3-6 word institutional title. No generic words like Ultimate or Complete.",
  "subtitle": "12-15 word subtitle naming the specific value delivered.",
  "target_audience_summary": "One sentence: who this is for and what specific outcome they get."
}}"""
        try:
            return self._call_ai(system, prompt)
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return {"title": signals["topic"], "subtitle": config["label"], "target_audience_summary": ""}

    def _generate_section(self, key, title, label, brief, signals, config, section_num) -> str:
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
- Every paragraph must address at least one of: {signals['pain_points']}
- Use specific metrics, percentages, financial figures — no vague statements
- NO filler: "it is important to note", "in today's world", "leveraging synergies"
- Institutional consulting grade — dense, analytical, specific
- Return valid JSON only. No markdown fences."""

        prompt = f"""Write Section {section_num}/15 for this {config['label']}.

SECTION TITLE: {title}
CONTENT BRIEF: {brief_filled}

REQUIREMENTS:
- Minimum 700 words for analysis sections, 500 for summary/conclusion sections
- ENTIRELY about {signals['topic']} — zero generic filler
- Name specific challenges from: {signals['pain_points']}
- At least 3 specific metrics or data points
- Flowing prose — not bullet lists unless document type is checklist
- HTML allowed: use <strong> for key terms, <p> for paragraphs, <h3> for subheadings

Return JSON: {{ "{key}": "full HTML-ready prose content here" }}"""

        try:
            result  = self._call_ai(system, prompt)
            content = result.get(key, "")
            if not content or len(content.split()) < 80:
                raise ValueError(f"Too short: {len(content.split())} words")
            return content
        except Exception as e:
            logger.error(f"❌ Section {key} failed: {e}. Retrying...")
            return self._retry_section(key, title, signals, config)

    def _retry_section(self, key, title, signals, config) -> str:
        prompt = (
            f'Write 500 words about "{title}" for {signals["topic"]} '
            f'addressing {signals["pain_points"]} for {signals["audience"]} '
            f'in {signals["industry"]}. Return JSON: {{"{key}": "prose"}}'
        )
        try:
            result = self._call_ai("You are a senior strategist. Return JSON only.", prompt)
            return result.get(key, f"<p>Strategic analysis of {title}.</p>")
        except Exception:
            return (
                f"<strong>{title}</strong>"
                f"<p>Strategic analysis of {signals['topic']} addressing "
                f"{signals['pain_points']} for {signals['audience']}.</p>"
            )

    def _call_ai(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> Dict:
        start    = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            response_format={"type": "json_object"},
        )
        duration = time.time() - start
        logger.info(f"✅ Groq | {duration:.2f}s | finish={response.choices[0].finish_reason}")

        if response.choices[0].finish_reason == "length":
            raise ValueError("Groq response truncated — max_tokens reached")

        return json.loads(response.choices[0].message.content)

    def _ensure_closed_tags(self, html: str) -> str:
        if not html:
            return html
        void_tags = {"br", "hr", "img", "input", "link", "meta"}
        tags  = re.findall(r"<(/?)([a-zA-Z1-6]+)", html)
        stack: List[str] = []
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
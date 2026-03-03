"""
perplexity_client.py — Senior Adaptive-Reuse Consultant Edition
Aligned to magazine-template-v5.html with 4-segment audience analysis.
"""

import os
from pathlib import Path
import json
import requests
import re
import logging
import concurrent.futures
import traceback
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

logger = logging.getLogger(__name__)


class PerplexityClient:
    """Client for Perplexity AI — generates all content for lead-magnet PDFs."""

    def __init__(self):
        if load_dotenv:
            for env_path in [
                Path(__file__).resolve().parents[1] / '.env',
                Path(__file__).resolve().parents[2] / '.env',
            ]:
                if env_path.exists():
                    try:
                        load_dotenv(env_path)
                        logger.info(f"✅ Loaded .env from: {env_path}")
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to load .env from {env_path}: {e}")

        self.api_key  = os.getenv('PERPLEXITY_API_KEY')
        self.base_url = "https://api.perplexity.ai/chat/completions"
        if not self.api_key:
            logger.warning("⚠️  PERPLEXITY_API_KEY not found in environment")
        else:
            logger.info("✅ PerplexityClient ready")

    def _is_meaningful(self, value: Any) -> bool:
        if value is None: return False
        if isinstance(value, list): return any(self._is_meaningful(i) for i in value)
        v = str(value).strip()
        if len(v) < 2: return False
        
        # Comprehensive list of filler/weak inputs to ignore
        FILLERS = {
            "test", "testing", "none", "n/a", "na", "null", "empty", "ok", "yes", "no",
            "placeholder", "asdf", "qwerty", "lorem", "ipsum", "...", "h", "ok.", ".", "–",
            "abc", "xyz", "stuff", "things", "data", "info", "etc", "...", "???"
        }
        return v.lower() not in FILLERS

    def interpret_field(self, field_value: Any) -> str:
        if not self._is_meaningful(field_value): 
            return "INFER_FROM_CONTEXT (The user provided a weak or placeholder input here. Please use your senior advisory expertise to infer the most logical institutional content based on the rest of the report context.)"
            
        cleaned = ", ".join(str(x).strip() for x in field_value) if isinstance(field_value, list) else " ".join(str(field_value).split())
        
        # Strengthen weak inputs for the AI
        if len(cleaned) < 4: # If single char or very short (e.g. "h", "abc")
            return "INFER_FROM_CONTEXT (Input was too short/vague. Infer elite institutional details.)"
            
        return f"REINTERPRET & EXPAND: {cleaned}"

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, str]:
        return {k: self.interpret_field(v) for k, v in user_answers.items()}

    def generate_lead_magnet_json(self, signals: Dict[str, str], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key: return self._build_fallback_content(signals, firm_profile)
        
        prompt = self._create_content_prompt(signals, firm_profile)
        system_prompt = (
            "You are a senior institutional adaptive-reuse consultant. "
            "Output ONLY valid JSON. "
            "STRICT REQUIREMENTS:\n"
            "1. NO markdown code fences (do not use ```json or ```).\n"
            "2. NO introductory or concluding text.\n"
            "3. NO commentary or explanations.\n"
            "4. Start with '{' and end with '}'.\n"
            "5. Follow the provided schema exactly.\n"
            "6. Ensure all strings are properly escaped for JSON.\n\n"
            "EXAMPLE OF VALID OUTPUT:\n"
            "{\"title\": \"Example Title\", \"summary\": \"Example Summary...\", ...}"
        )

        def attempt_generation(current_prompt: str, is_retry: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
            try:
                # Log attempt
                logger.info(f"🚀 AI Generation Attempt {'Retry' if is_retry else '1'}")
                
                response = requests.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}", 
                        "Content-Type": "application/json", 
                        "Accept": "application/json"
                    },
                    json={
                        "model": "sonar",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": current_prompt},
                        ],
                        "max_tokens": 4000,
                        "temperature": 0.5 if not is_retry else 0.2, # Low temp for deterministic JSON
                    },
                    timeout=90,
                )
                if response.status_code != 200:
                    logger.error(f"AI API Error: {response.status_code} - {response.text}")
                    return None, None
                
                raw = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                if not raw:
                    logger.warning("Empty content from AI")
                    return None, None

                # JSON Extraction Layer
                sanitized = self._extract_json(raw)
                try:
                    return json.loads(sanitized), raw
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON Decode Error (Attempt {'Retry' if is_retry else '1'}): {str(e)}\nRaw snippet: {raw[:100]}...")
                    return None, raw
            except Exception as e:
                logger.error(f"AI Generation Attempt Exception: {str(e)}\n{traceback.format_exc()}")
                return None, None

        # First Attempt
        result, failed_text = attempt_generation(prompt)
        
        # Retry Logic (One-time correction)
        if result is None:
            logger.info("🔄 Invalid JSON detected. Attempting one-time correction...")
            # If we have the failed text, ask the AI specifically to fix it
            if failed_text:
                correction_prompt = (
                    f"The following output was intended to be a valid JSON object but failed parsing. "
                    f"Please correct it and return ONLY the valid JSON object. No markdown, no extra text.\n\n"
                    f"FAILED OUTPUT:\n{failed_text}\n\n"
                    f"RE-OUTPUT VALID JSON NOW:"
                )
            else:
                correction_prompt = prompt # Fallback to original prompt
                
            result, _ = attempt_generation(correction_prompt, is_retry=True)

        if result:
            logger.info("✅ Deterministic AI generation successful")
            return result
        
        logger.error("❌ Deterministic AI generation failed after retries. Using fallback.")
        return self._build_fallback_content(signals, firm_profile)

    def _create_content_prompt(self, signals: Dict[str, str], firm_profile: Dict[str, Any]) -> str:
        main_topic = signals.get('main_topic', 'Adaptive Reuse Executive Guide')
        return f"""
Act as a Senior Institutional Adaptive-Reuse Consultant for Global Asset Managers. 
Generate an elite, 13-page Technical Advisory Report for '{main_topic}'.

The document must read like a McKinsey, BCG, or institutional advisory report. No fluff. No motivational filler. Use formal, technical, and precise language. Use positive, solution-oriented terminology. Focus on capabilities, strategic advantages, and outcomes. NEVER use the term "pain points" or emphasize negative framing.

DOCUMENT STRUCTURE (MANDATORY 9 SECTIONS):
1. EXECUTIVE SUMMARY: Accelerating Asset Value through Strategic Transformation.
2. STRATEGIC ADVANTAGE 1: TECHNICAL PRECISION & BIM INTEGRATION (Digital Twins, Structural Optimization, Envelope Excellence).
3. STRATEGIC ADVANTAGE 2: INSTITUTIONAL SYNERGY & COLLABORATION (Unified OAC Protocols, RFI Efficiency, Seamless Stakeholder Alignment).
4. STRATEGIC ADVANTAGE 3: REGULATORY AGILITY & POLICY LEVERAGE (Expedited Compliance, Zoning Unlock, Heritage Value Capture).
5. STRATEGIC ADVANTAGE 4: TIMELINE ACCELERATION & OPERATIONAL EXCELLENCE (Phased Abatement, Early Works Sequencing, Critical Path Optimization).
6. FINANCIAL PERFORMANCE MODELING: IRR Maximization, CapEx Efficiency, and Long-Term Asset Appreciation.
7. GOVERNANCE & STRATEGIC RISK TRANSFER: Proactive GMP Frameworks, CM-at-Risk, Latent Condition Management.
8. ESG LEADERSHIP & URBAN REGENERATION: Carbon Credit Monetization, Green Financing, Social Value Creation.
9. STRATEGIC PERFORMANCE DASHBOARD: Quantified Outcomes & Institutional KPIs.

FOR EVERY CHAPTER (MANDATORY CONTENT DENSITY):
- Target 1000 words of technical, data-backed consulting content per section.
- Convert short statements into deep structured analysis:
    - Root Cause Analysis (Technical & Operational factors)
    - Financial Impact Assessment (IRR, CapEx, Carrying Costs, Yield-on-Cost)
    - Technical Mechanism (The engineering or regulatory physics of the issue)
    - Quantified Performance Profile (Probability of success, Efficiency Gains, and Financial Upside)
    - Strategic Mitigation Framework (Step-by-step institutional intervention)
    - Performance Comparison (Quantified improvement metrics)
    - KPI Dashboard (3-5 specific, measurable institutional metrics)
- Include 3-4 additional technical sub-sections per chapter.
- Provide extreme technical detail on:
    - LiDAR-to-BIM: Point cloud density, feature extraction algorithms, and LOD 350+ modeling.
    - Heritage Envelopes: Dew point analysis, vacuum-insulated glazing (VIG) U-values, and breathability constraints.
    - ESG Financing: Green Bond frameworks, Brownfield Tax Credits, and Carbon Offset verification.
    - Risk Transfer: Latent condition allocation in legacy industrial shells.

OUTPUT — Return ONLY valid JSON:
{{
  "title": "{main_topic}", 
  "summary": "250-300 words of elite institutional overview focused on strategic advantage and asset yield.", 
  "outcome_statement": "Institutional value proposition: 25% schedule acceleration and 40% risk mitigation.",
  "key_insights": ["Insight 1: Technical", "Insight 2: Financial", "Insight 3: Regulatory", "Insight 4: Operational", "Insight 5: ESG"],
  "pull_quotes": ["Institutional Quote 1", "Institutional Quote 2", "Institutional Quote 3"],
  "stats": {{ "s1v": "Val", "s1l": "Label", "s2v": "V", "s2l": "L", "s3v": "V", "s3l": "L", "s4v": "V", "s4l": "L", "s5v": "V", "s5l": "L", "s6v": "V", "s6l": "L", "s7v": "V", "s7l": "L", "s8v": "V", "s8l": "L", "s9v": "V", "s9l": "L" }},
  "commercial_analysis": "ROI/NOI/IRR sensitivity analysis (300-350 words) for asset managers.",
  "government_analysis": "Urban Regeneration/ESG/PPP impact analysis (300-350 words) for municipal authorities.",
  "architect_analysis": "Technical/Design/Compliance impact analysis (300-350 words) for lead consultants.",
  "contractor_analysis": "Execution/Risk/Sequencing impact analysis (300-350 words) for construction partners.",
  "checklists": [ {{ "items": ["Step 1", "Step 2", "Step 3", "Step 4"] }}, {{ "items": ["Metric 1", "Metric 2", "Metric 3", "Metric 4"] }}, {{ "items": ["KPI 1", "KPI 2", "KPI 3"] }} ],
  "info_cards": [ {{ "label": "Case Study", "content": "Detailed institutional case summary" }}, {{ "label": "Financial Metric", "content": "Numeric breakdown" }}, {{ "label": "Technical Spec", "content": "Protocol detail" }}, {{ "label": "Risk Matrix", "content": "Allocation detail" }}, {{ "label": "ESG Bench", "content": "Performance detail" }}, {{ "label": "Timeline Bench", "content": "Compression detail" }}, {{ "label": "CapEx Bench", "content": "Predictability detail" }} ],
  "callouts": [ {{ "label": "STRATEGIC ANALYSIS", "content": "Deep dive detail" }}, {{ "label": "FINANCIAL IMPACT", "content": "IRR sensitivity detail" }}, {{ "label": "TECHNICAL PROTOCOL", "content": "Step-by-step detail" }}, {{ "label": "RISK MITIGATION", "content": "Intervention detail" }}, {{ "label": "KPI DASHBOARD", "content": "Measurable detail" }} ],
  "sections": [
    {
      "chapter_title": "EXECUTIVE SUMMARY",
      "chapter_subtitle": "Maximizing Asset Potential through Strategic Transformation",
      "opening_paragraph": "150 words of elite institutional overview...",
      "root_causes": ["Technical Precision", "Collaborative Synergy", "Regulatory Agility"],
      "quantified_impact": "Proactive retrofit management can improve project IRR by 400-600 basis points.",
      "intervention_framework": "Transition from reactive problem-solving to proactive data-backed governance.",
      "benchmark_case": "Metropolitan Retrofit: 40% faster speed-to-market.",
      "kpis": [{"before": "18% change order variance", "after": "7% precision"}],
      "comparison_table": [{"factor": "CapEx", "challenge": "Audit Investment", "response": "18% variance reduction"}]
    },
    {
      "chapter_title": "STRATEGIC ADVANTAGE 1: TECHNICAL PRECISION",
      "chapter_subtitle": "LiDAR-to-BIM Asset Intelligence",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{"before": "...", "after": "..."}],
      "comparison_table": [{"factor": "...", "challenge": "...", "response": "..."}]
    },
    {
      "chapter_title": "STRATEGIC ADVANTAGE 2: INSTITUTIONAL SYNERGY",
      "chapter_subtitle": "OAC Protocols & RFI Efficiency",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{"before": "...", "after": "..."}],
      "comparison_table": [{"factor": "...", "challenge": "...", "response": "..."}]
    },
    {
      "chapter_title": "STRATEGIC ADVANTAGE 3: REGULATORY AGILITY",
      "chapter_subtitle": "Heritage Compliance & Zoning Unlock",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{"before": "...", "after": "..."}],
      "comparison_table": [{"factor": "...", "challenge": "...", "response": "..."}]
    },
    {
      "chapter_title": "STRATEGIC ADVANTAGE 4: TIMELINE ACCELERATION",
      "chapter_subtitle": "Early Works Sequencing",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{"before": "...", "after": "..."}],
      "comparison_table": [{"factor": "...", "challenge": "...", "response": "..."}]
    },
    {
      "chapter_title": "FINANCIAL PERFORMANCE MODELING",
      "chapter_subtitle": "IRR Sensitivity & Asset Appreciation",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{"before": "...", "after": "..."}],
      "comparison_table": [{"factor": "...", "challenge": "...", "response": "..."}]
    },
    {
      "chapter_title": "GOVERNANCE & RISK TRANSFER",
      "chapter_subtitle": "Contractual Indemnity & Latent Conditions",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{"before": "...", "after": "..."}],
      "comparison_table": [{"factor": "...", "challenge": "...", "response": "..."}]
    },
    {
      "chapter_title": "ESG LEADERSHIP",
      "chapter_subtitle": "Embodied Carbon & Social Multipliers",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{"before": "...", "after": "..."}],
      "comparison_table": [{"factor": "...", "challenge": "...", "response": "..."}]
    },
    {
      "chapter_title": "STRATEGIC PERFORMANCE DASHBOARD",
      "chapter_subtitle": "Quantified Strategic Outcomes",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{"before": "...", "after": "..."}],
      "comparison_table": [{"factor": "...", "challenge": "...", "response": "..."}]
    }
  ],
  "call_to_action": { "headline": "Headline", "description": "Expert reasoning", "button_text": "Action" }
}
""".strip()

    def _extract_json(self, text: str) -> str:
        """Robust JSON extraction layer to handle AI output variability."""
        if not text: return ""
        
        # 1. Remove markdown code fences if present
        text = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', text).strip()
        
        # 2. Extract first JSON object from text using regex
        # Look for the first '{' and the last '}'
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        return text.strip()

    def normalize_ai_output(self, raw: Any) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "title": "", "summary": "", "outcome_statement": "",
            "key_insights": [], "pull_quotes": [], "stats": {},
            "commercial_analysis": "Strategic assessment for commercial stakeholders.", 
            "government_analysis": "Regulatory and urban impact assessment for government authorities.", 
            "architect_analysis": "Technical and structural considerations for architectural implementation.", 
            "contractor_analysis": "Logistical and construction sequencing for contractors.",
            "checklists": [], "info_cards": [], "callouts": [], "sections": [],
            "call_to_action": {"headline": "Start Your Project", "description": "Ready to move forward?", "button_text": "Connect Now"},
        }
        if not isinstance(raw, dict): return out
        def ct(v: Any, fb="") -> str: return str(v).strip() if v else fb
        out["title"] = ct(raw.get("title"))
        out["summary"] = ct(raw.get("summary"))
        out["outcome_statement"] = ct(raw.get("outcome_statement"))
        out["commercial_analysis"] = ct(raw.get("commercial_analysis"), out["commercial_analysis"])
        out["government_analysis"] = ct(raw.get("government_analysis"), out["government_analysis"])
        out["architect_analysis"] = ct(raw.get("architect_analysis"), out["architect_analysis"])
        out["contractor_analysis"] = ct(raw.get("contractor_analysis"), out["contractor_analysis"])
        out["key_insights"] = [ct(ki) for ki in raw.get("key_insights", []) if ki]
        out["pull_quotes"] = [ct(q) for q in raw.get("pull_quotes", []) if q]
        out["stats"] = {k: ct(v) for k, v in raw.get("stats", {}).items()}
        for cl in raw.get("checklists", []):
            if isinstance(cl, dict): out["checklists"].append({"items": [ct(i) for i in cl.get("items", []) if i]})
        for card in raw.get("info_cards", []):
            if isinstance(card, dict): out["info_cards"].append({"label": ct(card.get("label")), "content": ct(card.get("content"))})
        for co in raw.get("callouts", []):
            if isinstance(co, dict): out["callouts"].append({"label": ct(co.get("label")), "content": ct(co.get("content"))})
        
        # New Granular Sections Normalization
        for item in raw.get("sections", []):
            if isinstance(item, dict):
                normalized_section = {
                    "chapter_title": ct(item.get("chapter_title")),
                    "chapter_subtitle": ct(item.get("chapter_subtitle")),
                    "opening_paragraph": ct(item.get("opening_paragraph")),
                    "root_causes": [ct(rc) for rc in item.get("root_causes", []) if rc],
                    "quantified_impact": ct(item.get("quantified_impact")),
                    "intervention_framework": ct(item.get("intervention_framework")),
                    "benchmark_case": ct(item.get("benchmark_case")),
                    "kpis": [{"before": ct(k.get("before")), "after": ct(k.get("after"))} for k in item.get("kpis", []) if isinstance(k, dict)],
                    "comparison_table": [{"factor": ct(row.get("factor")), "challenge": ct(row.get("challenge")), "response": ct(row.get("response"))} for row in item.get("comparison_table", []) if isinstance(row, dict)]
                }
                out["sections"].append(normalized_section)
                
        cta = raw.get("call_to_action", {})
        if isinstance(cta, dict): out["call_to_action"] = {k: ct(cta.get(k), out["call_to_action"].get(k)) for k in ["headline", "description", "button_text"]}
        return out

    def map_to_template_vars(self, ai_content: Dict[str, Any], firm_profile: Optional[Dict[str, Any]] = None,
                             user_answers: Optional[Dict[str, Any]] = None, architectural_images: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            fp = firm_profile or {}
            ua = user_answers or {}
            imgs = architectural_images or []
            img1 = imgs[0] if len(imgs) >= 1 else "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='640' height='480'><rect width='100%' height='100%' fill='%23eeeeee'/></svg>"
            img2 = imgs[1] if len(imgs) >= 2 else img1
            img3 = imgs[2] if len(imgs) >= 3 else img1

            sections = ai_content.get("sections", [])
            while len(sections) < 12: sections.append({"title": f"Strategic Section {len(sections)+1}", "content": ""})
            def st(i, fb=""): return str(sections[i].get("title") or fb).strip()
            def sc(i, fb=""): return str(sections[i].get("content") or fb).strip()
            stats = ai_content.get("stats", {})
            def sv(k, fb=""): return str(stats.get(k) or fb)
            insights = ai_content.get("key_insights", []) or []
            quotes = ai_content.get("pull_quotes", []) or []
            cards = ai_content.get("info_cards", [])
            callouts = ai_content.get("callouts", [])
            def ins(i, fb=""): return str(insights[i]) if i < len(insights) else fb
            def quo(i, fb=""): return str(quotes[i]) if i < len(quotes) else fb
            def cl(i, fb=""): return str(cards[i].get("label") if i < len(cards) else fb)
            def cc(i, fb=""): return str(cards[i].get("content") if i < len(cards) else fb)
            def ol(i, fb=""): return str(callouts[i].get("label") if i < len(callouts) else fb)
            def oc(i, fb=""): return str(callouts[i].get("content") if i < len(callouts) else fb)
            def chk(i, j, fb=""): 
                try: return str(ai_content.get("checklists", [])[i].get("items", [])[j])
                except: return fb
            
            main_title = str(ai_content.get("title") or f"{ua.get('main_topic','Adaptive Reuse')} Executive Guide").strip()
            hl_parts = main_title.split(":", 1)
            hl1, hl2 = hl_parts[0].strip(), (hl_parts[1].strip() if len(hl_parts) > 1 else "Executive Guide")
            year = str(datetime.now().year)
            company = str(fp.get("firm_name") or "Expert Firm").strip()
            email = str(fp.get("work_email") or "").strip()
            phone = str(fp.get("phone_number") or "").strip()
            website = str(fp.get("firm_website") or "").strip()
            primary = str(fp.get("primary_brand_color") or "#2a5766")
            
            v = {
                "mainTitle": main_title, "documentTitle": main_title.upper(), "documentSubtitle": ai_content.get("summary",""),
                "companyName": company, "emailAddress": email, "phoneNumber": phone, "website": website, "footerText": f"© {year} {company}",
                "primaryColor": primary, "secondaryColor": fp.get("secondary_brand_color","#B8860B"),
                "tertiaryColor": "#1E3A5F", "accentColor": "#4F7A8B", "creamColor": "#F7F4EF", "inkColor": "#1A1A1A", "ruleColor": "#DDDDDD",
                "commercialAnalysis": ai_content.get("commercial_analysis", ""),
                "governmentAnalysis": ai_content.get("government_analysis", ""),
                "architectAnalysis": ai_content.get("architect_analysis", ""),
                "contractorAnalysis": ai_content.get("contractor_analysis", ""),
                "coverBrand": company.upper(),
                "coverAudience": "EXECUTIVE SERIES",
                "coverTitleBold": hl1.upper(),
                "coverTitleItalic": hl2,
                "coverFooterLeft": f"© {year} {company}",
                "coverFooterRight": "STRATEGIC ANALYSIS",
                "coverTagline": ai_content.get("outcome_statement","")[:80],
                "stat1Value": "100%", "stat1Label": "PROFESSIONAL", "stat2Value": "AI", "stat2Label": "OPTIMISED", "stat3Value": year, "stat3Label": "EDITION",
                "sectionTitle1": "Introduction", "pageNumber2": "2", "termsHeadline": f"{hl1}: {hl2}", "termsParagraph1": ai_content.get("summary",""),
                "termsPullQuote": quo(0, "Strategy is execution."), "termsCopyright": f"© {year} {company}",
                "keyInsight1": ins(0), "keyInsight2": ins(1), "keyInsight3": ins(2), "keyInsight4": ins(3), "keyInsight5": ins(4),
                "sectionTitle2": "Contents", "pageNumber3": "3", "tocHeadlineLine1": "Strategic", "tocHeadlineLine2": "Roadmap",
                "tocItem1": st(0), "tocSub1": sc(0)[:250] + "...",
                "tocItem2": st(1), "tocSub2": sc(1)[:250] + "...",
                "tocItem3": st(2), "tocSub3": sc(2)[:250] + "...",
                "tocItem4": st(3), "tocSub4": sc(3)[:250] + "...",
                "tocItem5": st(4), "tocSub5": sc(4)[:250] + "...",
                "tocItem6": st(5), "tocSub6": sc(5)[:250] + "...",
                "tocItem7": st(6), "tocSub7": sc(6)[:250] + "...",
                "tocItem8": st(7), "tocSub8": sc(7)[:250] + "...",
                "tocItem9": st(8), "tocSub9": sc(8)[:250] + "...",
                "chapter1Section": "CHAPTER 01", "chapter1Eyebrow": "EXECUTIVE", "chapter1Title": st(0), "chapter1Intro": sc(0)[:220], "chapter1Body1": sc(0), "dropCap1": (sc(0)[:1] or "S").upper(),
                "chapter2Section": "CHAPTER 02", "chapter2Eyebrow": "TECHNOLOGY", "chapter2Title": st(1), "chapter2Intro": sc(1)[:220], "chapter2Body1": sc(1), "dropCap2": (sc(1)[:1] or "O").upper(),
                "chapter3Section": "CHAPTER 03", "chapter3Eyebrow": "COMMUNICATION", "chapter3Title": st(2), "chapter3Intro": sc(2)[:220], "chapter3Body1": sc(2), "dropCap3": (sc(2)[:1] or "I").upper(),
                "chapter4Section": "CHAPTER 04", "chapter4Eyebrow": "APPROVALS", "chapter4Title": st(3), "chapter4Intro": sc(3)[:220], "chapter4Body1": sc(3), "dropCap4": (sc(3)[:1] or "C").upper(),
                "chapter5Section": "CHAPTER 05", "chapter5Eyebrow": "TIMELINES", "chapter5Title": st(4), "chapter5Intro": sc(4)[:220], "chapter5Body1": sc(4), "dropCap5": (sc(4)[:1] or "A").upper(),
                "chapter6Section": "CHAPTER 06", "chapter6Eyebrow": "FINANCIAL", "chapter6Title": st(5), "chapter6Intro": sc(5)[:220], "chapter6Body1": sc(5), "dropCap6": (sc(5)[:1] or "F").upper(),
                "chapter7Section": "CHAPTER 07", "chapter7Eyebrow": "RISK", "chapter7Title": st(6), "chapter7Intro": sc(6)[:220], "chapter7Body1": sc(6), "dropCap7": (sc(6)[:1] or "R").upper(),
                "chapter8Section": "CHAPTER 08", "chapter8Eyebrow": "ESG", "chapter8Title": st(7), "chapter8Intro": sc(7)[:220], "chapter8Body1": sc(7), "dropCap8": (sc(7)[:1] or "E").upper(),
                "chapter9Section": "CHAPTER 09", "chapter9Eyebrow": "OUTCOMES", "chapter9Title": st(8), "chapter9Intro": sc(8)[:220], "chapter9Body1": sc(8), "dropCap9": (sc(8)[:1] or "P").upper(),
                "imagePage4Url": img1, "imagePage5Url": img2, "imagePage6Url": img3,
                "imageCaption1": "Strategic Assessment", "imageCaption2": "Market Context", "imageCaption3": "Technical Audit",
                "callout1Title": ol(0, "STRATEGIC VISION"), "callout1Body": oc(0, "Adaptive reuse is the most sustainable form of urban regeneration."),
                "callout2Title": ol(1, "REGULATORY EDGE"), "callout2Body": oc(1, "Zoning overlays can be unlocked with the right technical data."),
                "callout3Title": ol(2, "TECHNICAL FEASIBILITY"), "callout3Body": oc(2, "Structural integrity determines the ceiling for asset transformation."),
                "callout4Title": ol(3, "IMPLEMENTATION FOCUS"), "callout4Body": oc(3, "Phasing ensures minimal operational disruption during retrofit."),
                "callout5Title": ol(4, "RISK MITIGATION"), "callout5Body": oc(4, "Hazardous material abatement is a prerequisite for project success."),
                "tradeoffsTitle": "Market Trade-offs",
                "tradeoff1Term": cl(0, "CapEx"), "tradeoff1Desc": cc(0, "Balancing structural reuse with modern system integration."),
                "tradeoff2Term": cl(1, "Heritage"), "tradeoff2Desc": cc(1, "Preserving character vs. achieving high-performance envelopes."),
                "tradeoff3Term": cl(2, "Carbon"), "tradeoff3Desc": cc(2, "Embodied carbon savings vs. operational energy demands."),
                "tradeoff4Term": cl(3, "Zoning"), "tradeoff4Desc": cc(3, "Existing use rights vs. proposed functional shifts."),
                "tradeoff5Term": cl(4, "Speed"), "tradeoff5Desc": cc(4, "Retrofit timelines vs. new build lead times."),
                "phase1Title": cl(5, "Audit & Assessment"), "phase1Desc": cc(5, "Detailed structural and hazardous material audits."),
                "phase2Title": cl(6, "Concept & Feasibility"), "phase2Desc": cc(6, "Aligning commercial goals with technical constraints."),
                "caseStudy1Title": "Metropolitan Retrofit", "caseStudy1Desc": "Transformation of a 1920s warehouse into Grade-A office space.", "caseStudy1Result": "40% faster speed-to-market.",
                "caseStudy2Title": "Urban Heritage Hub", "caseStudy2Desc": "Adaptive reuse of a heritage textile mill for mixed-use retail.", "caseStudy2Result": "25% lower CapEx per sq ft.",
                "engagementMethodsTitle": "Strategic Methodology",
                "method1Phase": "Audit", "method1Desc": chk(0, 0, "Structural integrity review."),
                "method2Phase": "Design", "method2Desc": chk(0, 1, "Heritage-compliant BIM modeling."),
                "method3Phase": "Abatement", "method3Desc": chk(1, 0, "Lead and asbestos remediation."),
                "method4Phase": "Systems", "method4Desc": chk(1, 1, "High-efficiency MEP integration."),
                "method5Phase": "Delivery", "method5Desc": chk(2, 0, "Final certification and tenant handover."),
                "ctaIntro1": "The transition from legacy asset to high-performance building requires technical precision and strategic vision.",
                "ctaIntro2": "Our adaptive reuse methodology ensures that every project meets commercial ROI, regulatory requirements, and sustainability goals.",
                "ctaEyebrow": "NEXT STEPS",
                "contactLabel1": "EMAIL", "contactValue1": email,
                "contactLabel2": "PHONE", "contactValue2": phone,
                "contactLabel3": "WEBSITE", "contactValue3": website.replace("https://","").replace("http://",""),
                "stat1v": sv("s1v", "85%"), "stat1l": sv("s1l", "Alignment"),
                "stat2v": sv("s2v", "2.4x"), "stat2l": sv("s2l", "Efficiency"),
                "ctaTitle": (ai_content.get("call_to_action") or {}).get("headline") or "Ready to De-Risk Your Conversion?",
                "ctaBody": (ai_content.get("call_to_action") or {}).get("description") or "Our methodology turns the four pain points of adaptive reuse into measurable competitive advantages through technical precision and strategic governance.",
                "ctaButtonText": (ai_content.get("call_to_action") or {}).get("button_text") or "Schedule a Technical Audit",
                "backCoverBrand": company.upper(),
                "backCoverTitle": main_title.upper(),
                "backCoverSub": "EXECUTIVE STRATEGY SERIES",
                "backCoverYear": year,
                "commercialAnalysis": ai_content.get("commercial_analysis", ""),
                "governmentAnalysis": ai_content.get("government_analysis", ""),
                "architectAnalysis": ai_content.get("architect_analysis", ""),
                "contractorAnalysis": ai_content.get("contractor_analysis", ""),
                "pageNumber4": "4", "pageNumber5": "5", "pageNumber6": "6", "pageNumber7": "7", "pageNumber8": "8", "pageNumber9": "9",
                "pageNumber10": "10", "pageNumber11": "11", "pageNumber12": "12"
            }
            return v
        except Exception:
            logger.error(f"❌ Mapping Guard: {traceback.format_exc()}")
            return {"mainTitle": "Expert Guide"}

    def _build_fallback_content(self, signals: Dict[str, Any], fp: Dict[str, Any]) -> Dict[str, Any]:
        main_topic = signals.get('main_topic', 'Adaptive Reuse').replace("REINTERPRET & EXPAND: ", "")
        return {
            "title": f"{main_topic} Institutional Strategic Advisory",
            "summary": "This institutional strategic assessment provides a data-backed technical mandate for accelerating the value of large-scale adaptive reuse. Focusing on Technical Precision, Institutional Synergy, Regulatory Agility, and Timeline Acceleration, the report details elite intervention models—including 3D LiDAR-to-BIM scanning, Project Information Models (PIM), and parallel heritage/zoning submission strategies. Prepared for institutional asset managers and municipal authorities, it provides the necessary technical and financial framework for achieving superior project IRR and ESG leadership in complex urban retrofits.",
            "outcome_statement": "Institutional value maximization through technical precision: 25% schedule acceleration and 40% risk mitigation.",
            "commercial_analysis": "Institutional stakeholders maximize IRR by leveraging technical precision and timeline acceleration. Strategic advantages include early-stage BIM integration (LOD 350+), which typically increases field efficiency by 18-25%. Phased construction sequencing is a core capability for maintaining Net Operating Income (NOI) during transformation, especially in mixed-use conversions where tenant retention is optimized through strategic phasing. Financial performance is enhanced by the 'Heritage Premium'—a 15-20% rental uplift typical for repositioned assets in prime urban locations. IRR sensitivity analysis indicates that accelerated approval cycles can improve institutional financing efficiency by 180-220 basis points. Yield-on-Cost (YoC) is maximized through structural reuse, saving 35-45% on core shell costs.",
            "government_analysis": "Government authorities and municipal planning boards prioritize ESG leadership and urban regeneration multipliers. Achieving the 'Regulatory Agility' advantage through parallel heritage and zoning submissions can compress urban planning cycles by 10-14 weeks. Every ton of embodied carbon saved through structural reuse represents a 60-75% reduction compared to new build GWP (Global Warming Potential), directly supporting municipal Net Zero leadership and social value creation. Public-Private Partnership (PPP) potential is maximized when technical audits provide a clear roadmap for brownfield tax credits and green bond eligibility. Urban regeneration creates a 4.0x multiplier effect on local economic activity through strategic placemaking and institutional talent attraction.",
            "architect_analysis": "Architectural implementation leverages a rigorous 'BIM-to-Field' protocol to ensure precision between design intent and physical reality. Achieving 'Technical Precision' via 3D LiDAR point-cloud generation reduces RFI volume by 32% in complex heritage conversions. Detailed thermal performance audits of heritage envelopes, including dew point analysis and vacuum-insulated glazing (VIG) feasibility, ensure superior energy performance standards. Design capabilities account for undocumented structural modifications over decades, ensuring that seismic and wind-load reinforcements are seamlessly integrated. LOD 350+ models are the foundation for coordination excellence in restricted heritage shells.",
            "contractor_analysis": "Contractors achieve superior execution through 'Timeline Acceleration' and proactive site management. Structured hazardous material protocols and live-building sequencing ensure operational excellence and safety leadership. Implementation of an 'Early Works' package methodology for abatement and structural reinforcement improves cost predictability by an average of 15% across the project lifecycle. CM-at-Risk models provide the necessary transparency during the discovery phase, while GMP (Guaranteed Maximum Price) ensures financial certainty. Critical Path Optimization leverages 10-15% risk-based buffers for 'Discovery Phase' adjustments, ensuring reliable delivery.",
            "key_insights": [
                "Insight 1: 3D LiDAR-to-BIM scanning increases structural precision by 35% vs traditional audits.",
                "Insight 2: Structured OAC communication models increase coordination efficiency by 16% on average.",
                "Insight 3: Parallel heritage/zoning submission strategies accelerate project commencement by 12 weeks.",
                "Insight 4: Phased hazardous material abatement accelerates overall schedule by 20% in urban cores.",
                "Insight 5: BIM-to-Field integration increases onsite efficiency by 45% in heritage shell retrofits."
            ],
            "pull_quotes": [
                "Strategic advantage in retrofit is defined by data precision, not just design aspiration.",
                "The value of seamless communication is not just speed; it is the compounding of institutional success.",
                "Technical precision in the audit phase is the primary driver of IRR maximization in complex retrofit."
            ],
            "stats": {
                "s1v": "25%", "s1l": "Schedule Acceleration",
                "s2v": "40%", "s2l": "Risk Mitigation",
                "s3v": "35%", "s3l": "Efficiency Gain",
                "s4v": "20%", "s4l": "CapEx Precision",
                "s5v": "70%", "s5l": "Carbon Savings",
                "s6v": "450bps", "s6l": "IRR Improvement",
                "s7v": "15%", "s7l": "Rental Premium",
                "s8v": "4.0x", "s8l": "Economic Multiplier",
                "s9v": "100%", "s9l": "Technical Audit"
            },
            "sections": [
                {
                    "chapter_title": "EXECUTIVE SUMMARY",
                    "chapter_subtitle": "Maximizing Asset Potential through Strategic Transformation",
                    "opening_paragraph": "The global adaptive reuse market offers significant opportunities for institutional investors to accelerate asset value and achieve market leadership. Focusing on Technical Precision, Collaborative Synergy, Regulatory Agility, and Timeline Acceleration, this report details elite intervention models that drive project IRR. Institutional developers are increasingly pivoting to retrofit, achieving 15-20% lower embodied carbon and significantly accelerated speed-to-market in supply-constrained urban cores.",
                    "root_causes": ["Technical Precision", "Collaborative Synergy", "Regulatory Agility"],
                    "quantified_impact": "Proactive retrofit management can improve project IRR by 400-600 basis points.",
                    "intervention_framework": "Transition from reactive problem-solving to proactive data-backed governance.",
                    "benchmark_case": "Metropolitan Retrofit: 40% faster speed-to-market.",
                    "kpis": [{"before": "18% variance", "after": "7% precision"}],
                    "comparison_table": [{"factor": "CapEx", "challenge": "Audit Investment", "response": "18% variance reduction"}]
                },
                {
                    "chapter_title": "STRATEGIC ADVANTAGE 1: TECHNICAL PRECISION",
                    "chapter_subtitle": "LiDAR-to-BIM Asset Intelligence",
                    "opening_paragraph": "Technical precision in adaptive reuse is achieved by bridging the delta between legacy documentation and actual site conditions. Leveraging 3D LiDAR point-cloud generation and LOD 350+ BIM modeling ensures structural optimization and envelope excellence, even in restricted heritage shells.",
                    "root_causes": ["Precision Auditing", "Digital Twin Integration", "Structural Optimization"],
                    "quantified_impact": "Structural precision typically reduces field rework by 35% vs traditional audits.",
                    "intervention_framework": "Mandatory 3D LiDAR point-cloud generation and LiDAR-to-BIM conversion prior to CD phase.",
                    "benchmark_case": "Warehouse conversion: LiDAR identified 150mm slab variance, saving $180k.",
                    "kpis": [{"before": "15-25% variance", "after": "7% precision"}],
                    "comparison_table": [{"factor": "Audit", "challenge": "Assumed dimensions", "response": "LOD 350+ verification"}]
                }
            ],
            "call_to_action": {
                "headline": "Ready to Maximize Your Institutional Asset?",
                "description": "Our senior consulting methodology turns the complexities of adaptive reuse into measurable strategic advantages through technical precision and data-backed governance.",
                "button_text": "Schedule an Institutional Technical Audit"
            }
        }

    def ensure_section_content(self, sections: List[Dict[str, Any]], signals: Dict[str, str], firm_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        while len(sections) < 9: 
            sections.append({
                "chapter_title": f"Strategic Focus {len(sections)+1}",
                "chapter_subtitle": "Institutional Assessment",
                "opening_paragraph": "Content pending generation...",
                "root_causes": [], "quantified_impact": "", "intervention_framework": "", "benchmark_case": "", "kpis": [], "comparison_table": []
            })
        
        def is_thin(section: Dict[str, Any]) -> bool:
            # Check if opening paragraph is too short
            return len(str(section.get("opening_paragraph", "")).split()) < 100

        indices_to_fix = [i for i, s in enumerate(sections) if is_thin(s)]
        if not indices_to_fix: return sections

        def regenerate_one(idx: int) -> Dict[str, Any]:
            section = sections[idx]
            title = section.get("chapter_title")
            prompt = f"""
            Institutional expert advisory report for chapter '{title}' regarding '{signals.get('main_topic')}'. 
            Output ONLY valid JSON for this chapter.
            SCHEMA:
            {{
              "chapter_title": "{title}",
              "chapter_subtitle": "...",
              "opening_paragraph": "150-200 words of technical analysis",
              "root_causes": ["...", "...", "..."],
              "quantified_impact": "...",
              "intervention_framework": "...",
              "benchmark_case": "...",
              "kpis": [{{"before": "...", "after": "..."}}],
              "comparison_table": [{{"factor": "...", "challenge": "...", "response": "..."}}]
            }}
            """
            try:
                resp = requests.post(self.base_url, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": "sonar", "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000, "temperature": 0.6}, timeout=90)
                if resp.status_code == 200:
                    raw_new = resp.json()['choices'][0]['message']['content']
                    sanitized = self._extract_json(raw_new)
                    new_data = json.loads(sanitized)
                    return self.normalize_ai_output({"sections": [new_data]})["sections"][0]
            except Exception as e:
                logger.error(f"Error regenerating section {idx}: {e}")
            return sections[idx]

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(regenerate_one, indices_to_fix))
            for i, idx in enumerate(indices_to_fix):
                sections[idx] = results[i]
        return sections

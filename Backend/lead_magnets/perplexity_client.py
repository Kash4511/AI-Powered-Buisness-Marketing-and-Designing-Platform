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

The document must read like a McKinsey, BCG, or institutional advisory report. No fluff. No motivational filler. Use formal, technical, and precise language.

DOCUMENT STRUCTURE (MANDATORY 9 SECTIONS):
1. EXECUTIVE SUMMARY: Solving the Retrofit Crisis through Strategic Asset Transformation.
2. PAIN POINT 1: TECHNICAL COMPLEXITY & STRUCTURAL INTEGRITY (LiDAR-to-BIM, Load-Bearing Analysis, Envelope Retrofits).
3. PAIN POINT 2: INSTITUTIONAL COMMUNICATION & STAKEHOLDER ALIGNMENT (OAC Protocols, RFI Streamlining, Change-Order Mitigation).
4. PAIN POINT 3: REGULATORY ACCELERATION & ZONING UNLOCKS (Heritage Compliance, Mixed-Use Fire/Life Safety, Policy Leverage).
5. PAIN POINT 4: TIMELINE COMPRESSION & HAZARDOUS LOGISTICS (Phased Abatement, Early Works Sequencing, Critical Path Optimization).
6. STRATEGIC FINANCIAL MODELING: IRR Sensitivity, CapEx Predictability, and Asset Appreciation.
7. RISK ALLOCATION & CONTRACTUAL GOVERNANCE: GMP vs CM-at-Risk, Latent Condition Indemnity.
8. ESG PERFORMANCE & URBAN REGENERATION: Embodied Carbon Credits, Green Financing, Social Value Multipliers.
9. PERFORMANCE DASHBOARD: Quantified Strategic Outcomes & Institutional KPIs.

FOR EVERY CHAPTER (MANDATORY CONTENT DENSITY):
- Target 1000 words of technical, data-backed consulting content per section.
- Convert short statements into deep structured analysis:
    - Root Cause Analysis (Technical & Operational factors)
    - Financial Impact Assessment (IRR, CapEx, Carrying Costs, Yield-on-Cost)
    - Technical Mechanism (The engineering or regulatory physics of the issue)
    - Quantified Risk Profile (Probability, Severity, and Financial Exposure)
    - Strategic Mitigation Framework (Step-by-step institutional intervention)
    - Before vs After Comparison (Quantified performance metrics)
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
  "summary": "250-300 words of elite institutional overview focused on strategic risk mitigation and asset yield.", 
  "outcome_statement": "Institutional value proposition: 25% schedule compression and 40% risk reduction.",
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
    {{ "title": "Executive Summary", "content": "1000 words of dense institutional analysis..." }},
    {{ "title": "Pain Point 1: Technical Complexity", "content": "1000 words following structured analysis format..." }},
    {{ "title": "Pain Point 2: Communication", "content": "1000 words following structured analysis format..." }},
    {{ "title": "Pain Point 3: Approvals", "content": "1000 words following structured analysis format..." }},
    {{ "title": "Pain Point 4: Timelines", "content": "1000 words following structured analysis format..." }},
    {{ "title": "Strategic Financial Modeling", "content": "1000 words following structured analysis format..." }},
    {{ "title": "Risk Allocation & Contract Strategy", "content": "1000 words following structured analysis format..." }},
    {{ "title": "ESG & Urban Regeneration", "content": "1000 words following structured analysis format..." }},
    {{ "title": "Performance Dashboard", "content": "1000 words following structured analysis format..." }}
  ],
  "call_to_action": {{ "headline": "Headline", "description": "Expert reasoning", "button_text": "Action" }}
}}
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
        for item in raw.get("sections", []):
            if isinstance(item, dict): out["sections"].append({"title": ct(item.get("title")), "content": ct(item.get("content"))})
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
            "title": f"{main_topic} Institutional Advisory Report",
            "summary": "This institutional strategic assessment provides a data-backed technical mandate for navigating the complexities of large-scale adaptive reuse. Focusing on Technical Complexity, Institutional Communication, Regulatory Acceleration, and Timeline Compression, the report details elite intervention models—including 3D LiDAR-to-BIM scanning, Project Information Models (PIM), and parallel heritage/zoning submission strategies. Prepared for institutional asset managers and municipal authorities, it provides the necessary technical and financial framework for achieving predictable project IRR and superior ESG performance in complex urban retrofits.",
            "outcome_statement": "Institutional de-risking of complex retrofit assets through technical precision: 25% schedule compression and 40% risk reduction.",
            "commercial_analysis": "Institutional stakeholders face significant IRR erosion from unmanaged technical complexity and timeline slippage. Mitigation requires early-stage BIM integration (LOD 350+), which typically reduces field rework by 18-25%. Phased construction sequencing is mandatory to maintain Net Operating Income (NOI) during main works, especially in mixed-use conversions where tenant retention is critical for CapEx amortization. Financial modeling must account for the 'Heritage Premium'—a 15-20% rental uplift typical for repositioned assets in prime urban locations. IRR sensitivity analysis indicates that a 3-month approval delay costs approximately 180-220 basis points in institutional financing charges and carrying costs. Yield-on-Cost (YoC) is optimized through structural reuse, saving 35-45% on core shell costs.",
            "government_analysis": "Government authorities and municipal planning boards prioritize ESG compliance and urban regeneration multiplier effects. Addressing the 'Approvals' bottleneck through parallel heritage and zoning submissions can compress urban planning cycles by 10-14 weeks. Every ton of embodied carbon saved through structural reuse represents a 60-75% reduction compared to new build GWP (Global Warming Potential), directly aligning with municipal Net Zero mandates and social value frameworks. Public-Private Partnership (PPP) leverage is maximized when technical audits provide a clear roadmap for brownfield tax credits and green bond eligibility. Urban regeneration creates a 4.0x multiplier effect on local economic activity through strategic placemaking and institutional talent attraction.",
            "architect_analysis": "Architectural implementation requires a rigorous 'BIM-to-Field' protocol to manage the delta between legacy documentation and as-built reality. Solving 'Technical Complexity' via 3D LiDAR point-cloud generation reduces RFI escalation patterns by 32% in complex heritage conversions. Detailed thermal bridging audits of heritage envelopes, including dew point analysis and vacuum-insulated glazing (VIG) feasibility, are required to meet modern Part L/Title 24 energy performance standards. Modeling constraints must account for undocumented structural modifications over decades, ensuring that seismic and wind-load reinforcements are integrated without compromising heritage character. LOD 350+ models are the prerequisite for coordination in restricted floor-to-ceiling heritage shells.",
            "contractor_analysis": "Contractors carry the highest execution risk from 'Timeline Compression' and latent site conditions. Structured hazardous material protocols (Asbestos/Lead) and live-building sequencing are prerequisites for maintaining liability buffers and safety standards. Implementation of an 'Early Works' package methodology for abatement and structural reinforcement reduces surprise reinforcement costs by an average of 15% across the core project lifecycle. GMP (Guaranteed Maximum Price) models are recommended for execution, while CM-at-Risk provides greater transparency during the discovery phase. Critical Path Optimization requires 10-15% risk-based buffers for 'Discovery Phase' adjustments in heritage assets.",
            "key_insights": [
                "Insight 1: 3D LiDAR-to-BIM scanning reduces structural surprise variance by 35% vs traditional audits.",
                "Insight 2: Structured OAC communication models decrease change-order inflation by 16% on average.",
                "Insight 3: Parallel heritage/zoning submission strategies accelerate project commencement by 12 weeks.",
                "Insight 4: Phased hazardous material abatement compresses overall schedule by 20% in urban cores.",
                "Insight 5: BIM-to-Field integration reduces onsite RFI volume by 45% in heritage shell retrofits."
            ],
            "pull_quotes": [
                "Institutional de-risking in retrofit is defined by data management, not just design aspiration.",
                "The cost of poor communication is not just delay; it is the compounding of institutional risk.",
                "Technical precision in the audit phase is the only hedge against IRR erosion in complex retrofit."
            ],
            "stats": {
                "s1v": "25%", "s1l": "Schedule Compression",
                "s2v": "40%", "s2l": "Risk Reduction",
                "s3v": "35%", "s3l": "RFI Reduction",
                "s4v": "20%", "s4l": "CapEx Predictability",
                "s5v": "70%", "s5l": "Carbon Savings",
                "s6v": "450bps", "s6l": "IRR Improvement",
                "s7v": "15%", "s7l": "Rental Premium",
                "s8v": "4.0x", "s8l": "Economic Multiplier",
                "s9v": "100%", "s9l": "Technical Audit"
            },
            "sections": [
                {
                    "title": "EXECUTIVE SUMMARY: Solving the Retrofit Crisis through Strategic Asset Transformation",
                    "content": "The global adaptive reuse market is currently constrained by four primary pain points that drive institutional CapEx variance and timeline slippage: Technical Complexity, Communication silos, Approval bottlenecks, and unpredictable Timelines. This guide provides a technical mandate for navigating these challenges using elite intervention models. Institutional developers are increasingly pivoting to retrofit over demolition, driven by 15-20% lower embodied carbon and significantly accelerated speed-to-market in supply-constrained urban cores. Root Cause: Failure typically resides in the delta between legacy documentation and physical site reality. Technical Mechanism: Misalignment between design intent and physical reality triggers late-stage field modifications, which are 3-5x more expensive than pre-construction adjustments. Financial Impact: Unmanaged retrofit risk can erode project IRR by 400-600 basis points. Mitigation: Transition from reactive problem-solving to proactive data-backed governance, ensuring that every design decision is grounded in measurable site constraints via early-stage technical audits and LiDAR-to-BIM conversion. KPIs: 45% reduction in onsite RFIs and a 15% improvement in CapEx predictability. Before: 18% change order risk from latent conditions. After: 7% change order variance via precision data."
                },
                {
                    "title": "PAIN POINT 1: TECHNICAL COMPLEXITY & STRUCTURAL INTEGRITY (LiDAR-to-BIM & Envelope Retrofits)",
                    "content": "Problem: Technical complexity in adaptive reuse stems from the delta between legacy documentation and actual site conditions. Technical Root Causes: Undocumented structural modifications over decades, thermal bridging in heritage envelopes, and MEP routing constraints within restricted floor-to-ceiling heights. LiDAR-to-BIM Workflow: 1) High-density point-cloud generation (±2mm accuracy). 2) Automated feature extraction for structural members. 3) Integration of MEP point-clouds into existing heritage models (LOD 350+). 4) Verification of floor slab levels and wall verticality. Quantified Impact: Unmanaged complexity leads to a 15-25% increase in change orders and a 32% RFI escalation rate. Financial Impact: Structural surprises typically account for 60% of contingency drawdown. Mitigation: Mandatory 3D LiDAR point-cloud generation and LiDAR-to-BIM conversion prior to CD phase. Technical Mechanism: Precise point-cloud data eliminates the 'Assumed Dimension' risk in architectural modeling. Before: 18% change order risk from latent conditions. After: 7% change order variance via precision data. KPIs: 40% reduction in onsite structural RFIs. Micro-case: In a 150,000 sq ft warehouse conversion, LiDAR identified a 150mm floor slab variance that would have cost $180k in remedial leveling if discovered during fit-out."
                },
                {
                    "title": "PAIN POINT 2: INSTITUTIONAL COMMUNICATION & STAKEHOLDER ALIGNMENT (OAC & PIM)",
                    "content": "Problem: Misalignment between Owner, Architect, and Contractor (OAC) typically triggers change-order inflation and sequencing conflicts. Technical Root Causes: Delayed feedback loops from approval authorities and fragmented Project Information Models (PIM). Mechanism: Asynchronous information flow leads to procurement errors and trade sequencing clashes in restricted heritage sites. Mitigation: Implementation of a centralized Project Information Model (PIM) and a structured coordination governance framework with 48-hour RFI response mandates. Quantified Risk: Poor communication adds 5-10% to total project CapEx and delays delivery by an average of 14 weeks. Mitigation Framework: 1) Unified CDE (Common Data Environment) setup. 2) Weekly automated clash detection reports. 3) RFI escalation matrix with clear liability triggers. Before: 14-week communication breakdown delay. After: 3-week decision response cycle. KPIs: 30% faster decision-making cycles and 18% reduction in coordination-driven change orders. Micro-case: A heritage mill conversion utilized a digital RFI dashboard to resolve 90% of coordination issues within the 48-hour mandate, saving 7 weeks of idle trade time."
                },
                {
                    "title": "PAIN POINT 3: REGULATORY ACCELERATION & ZONING UNLOCKS (Heritage & Policy Leverage)",
                    "content": "Problem: Approval delays are driven by incomplete documentation regarding heritage preservation and change-of-use permissions. Technical Root Causes: Sequential zoning overlays and lack of early-stage fire/life-safety compliance audits. Quantified Impact: Approval bottlenecks can stall projects for 6-18 months, reducing project IRR by 400-600 basis points. Mechanism: Permit dependency chains create critical-path slippage when heritage boards request mid-stream design revisions. Mitigation: Parallel submission strategy combined with early engagement ('Pre-App') with planning authorities and comprehensive heritage envelope audits. Strategy: Unlock zoning overlays via urban policy leverage, demonstrating how residential conversion supports municipal housing targets. Technical Protocol: Submit Heritage Impact Assessments (HIA) and Environmental Audits in parallel with Zoning Variance applications. Before: 12-month average approval cycle. After: 6-month approval cycle via precision documentation. KPIs: 18-week reduction in total permit acquisition time. Micro-case: By submitting heritage and environmental permits in parallel for a downtown retrofit, the developer shaved 5 months off the financing cost, saving $320k in interest carry."
                },
                {
                    "title": "PAIN POINT 4: TIMELINE COMPRESSION & HAZARDOUS LOGISTICS (Early Works Sequencing)",
                    "content": "Problem: Long timelines are primarily driven by unknown site conditions and hazardous material surprises during main works. Technical Root Causes: Asbestos/lead abatement and structural reinforcement surprises in heritage shells. Quantified Impact: Timeline slippage reduces project IRR by 3-6 points and increases construction financing costs by 15-18%. Mechanism: Discovery of hazardous materials during main trade works disrupts the entire trade sequencing chain. Mitigation: Early Works Package Sequencing: 1) Structural audit and hazardous material survey. 2) Strip-out and abatement under early works contract. 3) Main works contract commencement only after 'Safe Site' certification. Phased construction sequencing allocates 10-15% risk-based buffers. Before: 28-month projected timeline for complex retrofit. After: 22-month delivery via early works packages. KPIs: 20% schedule compression. Micro-case: A phased abatement strategy in an industrial-to-office conversion allowed fit-out trades to commence 4 months early, resulting in a $520k early-tenant-move-in premium."
                },
                {
                    "title": "STRATEGIC FINANCIAL MODELING: IRR Sensitivity, CapEx Predictability, and Asset Appreciation",
                    "content": "Elite institutional financial modeling for adaptive reuse must account for the 'Heritage Premium' and CapEx sensitivity. GMP vs CM-at-Risk: GMP models are recommended for execution risk transfer, while CM-at-Risk provides the necessary transparency during the discovery phase of heritage conversions. Financial Modeling Breakdown: Structural reuse typically saves 35-45% on core shell costs but requires a 15-18% increase in MEP spend to accommodate heritage shell constraints. IRR Sensitivity: A 3-month approval delay costs approximately 200 basis points in institutional financing charges. Repositioning Valuation: Strategic conversion of vacant Grade-B office assets into mixed-use hubs attracts high-value talent and increases municipal tax revenue by 15-20%. ESG Financing: Leverage green bonds and brownfield tax credits to offset initial audit costs. A comparison of Demolition vs Retrofit ROI shows that while retrofit CapEx may be 5-10% higher initially, the 25% faster speed-to-market and 65% lower carbon footprint result in a superior 5-year IRR for institutional investors. Technical Mechanism: Capitalizing on existing structural value reduces 'Yield-on-Cost' (YoC) barriers by 150-250 bps."
                },
                {
                    "title": "RISK ALLOCATION & CONTRACTUAL GOVERNANCE: GMP vs CM-at-Risk & Latent Conditions",
                    "content": "Standard contract models often fail in institutional adaptive reuse due to improper risk transfer regarding latent site conditions. Technical Intervention: Risk Transfer Matrix: Allocates 'Existing Condition' risk to the Owner while shifting 'Execution' and 'Sequencing' risk to the Contractor through GMP (Guaranteed Maximum Price) models. Insurance Frameworks: Live-building retrofits require specialized 'Surrounding Property' and hazardous material liability coverage. Contingency Allocation: Implementation of a structured contingency allocation (typical range 10-15%) reduces dispute volume by 40% by providing a clear mechanism for 'Discovery Phase' adjustments. Dispute Reduction: 35% reduction in legal claims achieved via mandatory pre-construction structural audits and 3D point-cloud verification. Liability Frameworks: Clearly define hazardous material abatement boundaries to prevent RFI escalation during main works sequencing. Contractual Mechanism: Use of AIA A133 or similar CM-at-Risk agreements allows for early contractor engagement during the 'Technical Audit' phase."
                },
                {
                    "title": "ESG PERFORMANCE & URBAN REGENERATION: Embodied Carbon & Green Financing",
                    "content": "Adaptive reuse is the primary lever for urban ESG performance and social value generation. Embodied Carbon: Structural reuse saves an average of 650-800kg CO2/m2 compared to new build construction. Operational Energy: High-performance envelope retrofitting, including internal wall insulation, vacuum glazing, and dew point analysis, achieves 45-50% reduction in kWh/m2/year. ESG Financing Instruments: Green bonds and carbon offset credits provide 150-200 bps financing advantages for deep-retrofit projects. Social Value: Brownfield regeneration creates a 4.0x multiplier effect on local economic activity through urban placemaking and Public-Private Partnership (PPP) leverage. Urban Regeneration: Strategic conversions revitalization declining urban cores, attracting high-value institutional talent and increasing municipal tax revenue by 15-22% post-completion. Social impact metrics must include community placemaking and heritage preservation value. Technical Protocol: Verification of carbon credits requires rigorous as-built structural verification (LiDAR-to-BIM)."
                },
                {
                    "title": "PERFORMANCE DASHBOARD: Quantified Strategic Outcomes & Institutional KPIs",
                    "content": "Institutional Performance Report: 1) Approval Cycle Reduction: 5 months saved via parallel submission. 2) Change Order Reduction: 15% decrease through LiDAR point-cloud audits. 3) RFI Volume Reduction: 45% via BIM-to-Field coordination. 4) Schedule Compression: 20% through early works abatement packages. 5) IRR Improvement: 450 bps through optimized financing and rental premium. 6) Asset Value Uplift: 30% post-repositioning. 7) CapEx Predictability: 18% variance reduction. 8) Embodied Carbon Savings: 70% vs new build GWP. Institutional Benchmarking: A 200,000 sq ft heritage mill conversion achieved 22-month delivery (vs 28-month baseline) with only 7% change order variance, resulting in a 26% project IRR. This dashboard provides the necessary data-backed evidence for asset managers to approve deep-retrofit mandates over traditional demolition-rebuild models. KPI Framework: Target <10% contingency drawdown and >15% rental premium post-repositioning."
                }
            ],
            "call_to_action": {
                "headline": "Ready to De-Risk Your Institutional Asset?",
                "description": "Our senior consulting methodology turns the four pain points of adaptive reuse into measurable competitive advantages through technical precision and data-backed institutional governance.",
                "button_text": "Schedule an Institutional Technical Audit"
            }
        }

    def ensure_section_content(self, sections: List[Dict[str, str]], signals: Dict[str, str], firm_profile: Dict[str, Any]) -> List[Dict[str, str]]:
        while len(sections) < 9: sections.append({"title": f"Strategic Focus {len(sections)+1}", "content": ""})
        def is_thin(text: str) -> bool: return len(text.split()) < 500 # Threshold for elite institutional density
        indices_to_fix = [i for i, s in enumerate(sections) if is_thin(s.get("content", ""))]
        if not indices_to_fix: return sections
        def regenerate_one(idx: int) -> Dict[str, str]:
            title = sections[idx].get("title")
            prompt = f"Institutional expert advisory report for '{title}' regarding '{signals.get('main_topic')}'. Write 1000 words of technical, data-backed institutional consulting content. No fluff. Include metrics, technical protocols, Root Cause, Financial Impact, Technical Mechanism, Quantified Risk, Mitigation Framework, and Before vs After comparison."
            try:
                resp = requests.post(self.base_url, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": "sonar", "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000, "temperature": 0.6}, timeout=90)
                if resp.status_code == 200:
                    new_content = resp.json()['choices'][0]['message']['content']
                    return {"title": title, "content": new_content}
            except Exception as e:
                logger.error(f"Error regenerating section {idx}: {e}")
            return sections[idx]

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(regenerate_one, indices_to_fix))
            for i, idx in enumerate(indices_to_fix):
                sections[idx] = results[i]
        return sections

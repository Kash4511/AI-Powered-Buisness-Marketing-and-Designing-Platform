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
from typing import Dict, Any, Optional, List
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
        FILLERS = {"test","testing","none","n/a","na","null","empty","ok","yes","no",
                   "placeholder","asdf","qwerty","lorem","ipsum","...","h","ok.",".","–"}
        return v.lower() not in FILLERS

    def interpret_field(self, field_value: Any) -> str:
        if not self._is_meaningful(field_value): return "INFER_FROM_CONTEXT"
        cleaned = ", ".join(str(x).strip() for x in field_value) if isinstance(field_value, list) else " ".join(str(field_value).split())
        return "INFER_FROM_CONTEXT" if len(cleaned) < 2 else f"REINTERPRET: {cleaned}"

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, str]:
        return {k: self.interpret_field(v) for k, v in user_answers.items()}

    def generate_lead_magnet_json(self, signals: Dict[str, str], firm_profile: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key: return self._build_fallback_content(signals, firm_profile)
        try:
            response = requests.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Accept": "application/json"},
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "You are a senior adaptive-reuse consultant. Output ONLY valid JSON. No markdown. No commentary."},
                        {"role": "user", "content": self._create_content_prompt(signals, firm_profile)},
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.7,
                },
                timeout=60,
            )
            if response.status_code != 200: return self._build_fallback_content(signals, firm_profile)
            raw = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
            return json.loads(self._extract_json_from_markdown(raw))
        except Exception:
            return self._build_fallback_content(signals, firm_profile)

    def _create_content_prompt(self, signals: Dict[str, str], firm_profile: Dict[str, Any]) -> str:
        main_topic = signals.get('main_topic', 'Adaptive Reuse Executive Guide')
        return f"""
You are a senior adaptive-reuse consultant with 20+ years of experience delivering complex commercial, heritage, and mixed-use retrofit projects.
You are refining an existing Adaptive Reuse Executive Guide to elite consultant-grade depth for investors, city officials, and institutional developers.

CORE RULE: INCREASE VISUAL DENSITY & INTELLECTUAL DEPTH.
Do NOT use generic filler. Every paragraph must provide technical value.

DOCUMENT STRUCTURE (MANDATORY 9 SECTIONS):
1. EXECUTIVE SUMMARY: Solving the Retrofit Crisis.
2. PAIN POINT 1: TECH COMPLEXITY (BIM, LiDAR, Structural).
3. PAIN POINT 2: COMMUNICATION BREAKDOWNS (OAC, RFI, Change-Order).
4. PAIN POINT 3: APPROVAL ACCELERATION (Zoning, Heritage).
5. PAIN POINT 4: TIMELINE COMPRESSION (Surprises, Logistics).
6. FINANCIAL MODELING & INVESTMENT STRATEGY.
7. RISK ALLOCATION & CONTRACT STRATEGY.
8. ESG & URBAN REGENERATION IMPACT.
9. PERFORMANCE DASHBOARD (Outcomes & KPIs).

FOR EVERY CHAPTER (MANDATORY CONTENT DENSITY):
- Target 500-700 words of technical analysis.
- Replace one-sentence statements with 4-6 sentence structured technical explanations.
- Include at least 3 measurable metrics (e.g., % CapEx variance, RFI reduction %, kWh/m2/year).
- Include 1 micro-case example (e.g., "In a Grade-II listed warehouse conversion in London...").
- Use technical sub-sections and structured bullet diagnostics.
- Reference specific protocols: BIM coordination, LiDAR-to-BIM, Hazardous material abatement (asbestos/lead), Zoning overlays, Heritage envelope performance.

FOR PAIN POINTS (SECTIONS 2-5):
- Root cause explanation + Quantified impact + Mechanism (why it occurs) + Step-by-step mitigation model + Before/After comparison.

OUTPUT — Return ONLY valid JSON:
{{
  "title": "{main_topic}", 
  "summary": "120-150 words of dense strategic overview.", 
  "outcome_statement": "Elite value proposition (max 80 chars).",
  "key_insights": ["Insight 1", "Insight 2", "Insight 3", "Insight 4", "Insight 5"],
  "pull_quotes": ["Expert Quote 1", "Expert Quote 2", "Expert Quote 3"],
  "stats": {{ "s1v": "Val", "s1l": "Label", "s2v": "V", "s2l": "L", "s3v": "V", "s3l": "L", "s4v": "V", "s4l": "L", "s5v": "V", "s5l": "L", "s6v": "V", "s6l": "L", "s7v": "V", "s7l": "L", "s8v": "V", "s8l": "L", "s9v": "V", "s9l": "L" }},
  "commercial_analysis": "ROI/NOI impact analysis (200-250 words).",
  "government_analysis": "ESG/Carbon/Regeneration impact (200-250 words).",
  "architect_analysis": "Design/Constraints/BIM impact (200-250 words).",
  "contractor_analysis": "Risk/Sequencing/Liability impact (200-250 words).",
  "checklists": [ {{ "items": ["Step 1", "Step 2", "Step 3", "Step 4"] }}, {{ "items": ["Metric 1", "Metric 2", "Metric 3", "Metric 4"] }}, {{ "items": ["KPI 1", "KPI 2", "KPI 3"] }} ],
  "info_cards": [ {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }} ],
  "callouts": [ {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }} ],
  "sections": [
    {{ "title": "Section 1 Title", "content": "500-700 words of technical depth..." }},
    {{ "title": "Section 2 Title", "content": "500-700 words of technical depth..." }},
    {{ "title": "Section 3 Title", "content": "500-700 words of technical depth..." }},
    {{ "title": "Section 4 Title", "content": "500-700 words of technical depth..." }},
    {{ "title": "Section 5 Title", "content": "500-700 words of technical depth..." }},
    {{ "title": "Section 6 Title", "content": "500-700 words of technical depth..." }},
    {{ "title": "Section 7 Title", "content": "500-700 words of technical depth..." }},
    {{ "title": "Section 8 Title", "content": "500-700 words of technical depth..." }},
    {{ "title": "Section 9 Title", "content": "500-700 words of technical depth..." }}
  ],
  "call_to_action": {{ "headline": "Headline", "description": "Expert reasoning", "button_text": "Action" }}
}}
""".strip()

    def _extract_json_from_markdown(self, text: str) -> str:
        if not text: return ""
        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if m: text = m.group(1).strip()
        a, b = text.find('{'), text.rfind('}')
        if a == -1 or b == -1: return text.strip()
        return text[a:b + 1].strip()

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
                "pageNumber4": "4", "pageNumber5": "5", "pageNumber6": "6", "pageNumber7": "7", "pageNumber8": "8", "pageNumber9": "9",
                "pageNumber10": "10", "pageNumber11": "11", "pageNumber12": "12"
            }
            return v
        except Exception:
            logger.error(f"❌ Mapping Guard: {traceback.format_exc()}")
            return {"mainTitle": "Expert Guide"}

    def _build_fallback_content(self, signals: Dict[str, Any], fp: Dict[str, Any]) -> Dict[str, Any]:
        main_topic = signals.get('main_topic', 'Adaptive Reuse').replace("REINTERPRET: ", "")
        return {
            "title": f"{main_topic} Executive Guide",
            "summary": "This elite strategic assessment provides a data-backed technical mandate for navigating the four critical pain points of adaptive reuse: Tech Complexity, Communication, Approvals, and Timelines. By implementing senior-level intervention models—including 3D LiDAR scanning, Project Information Models (PIM), and parallel submission strategies—institutional developers can achieve predictable ROI and superior asset performance in complex urban retrofits.",
            "outcome_statement": "Maximize asset value through expert-led mitigation of high-density retrofit risks.",
            "commercial_analysis": "Commercial stakeholders face significant IRR erosion from unmanaged tech complexity and timeline slippage. Mitigation requires early-stage BIM integration, which typically reduces field rework by 15-22%. Phased construction sequencing is mandatory to maintain Net Operating Income (NOI) during main works, especially in mixed-use conversions where tenant retention is critical for CapEx amortization.",
            "government_analysis": "Government authorities prioritize ESG compliance and urban regeneration multiplier effects. Addressing the 'Approvals' bottleneck through parallel heritage and zoning submissions can compress urban planning cycles by 8-12 weeks. Every ton of embodied carbon saved through structural reuse represents a 60-70% reduction compared to new build GWP (Global Warming Potential), aligning with municipal Net Zero mandates.",
            "architect_analysis": "Architectural implementation requires a rigorous 'BIM-to-Field' protocol to manage the delta between legacy documentation and as-built reality. Solving 'Tech Complexity' via 3D LiDAR point-cloud generation reduces RFI escalation patterns by 28% in complex heritage conversions. Detailed thermal bridging audits of heritage envelopes are required to meet modern Part L/Title 24 energy performance standards.",
            "contractor_analysis": "Contractors carry the highest execution risk from 'Long Timelines' and latent site conditions. Structured hazardous material protocols (Asbestos/Lead) and live-building sequencing are prerequisites for maintaining liability buffers. Implementation of a 'Mapping Guard' for legacy structural reinforcements reduces surprise reinforcement costs by an average of 12% across the core project lifecycle.",
            "key_insights": [
                "3D LiDAR scanning reduces structural surprise variance by 32% vs traditional site audits.",
                "Structured OAC communication models decrease change-order inflation by 14% on average.",
                "Parallel heritage/zoning submission strategies accelerate project commencement by 10 weeks.",
                "Phased hazardous material abatement compresses overall schedule by 18% in dense urban cores.",
                "BIM-to-Field integration reduces onsite RFI volume by 42% in heritage shell retrofits."
            ],
            "pull_quotes": [
                "Technical precision in the audit phase is the only hedge against IRR erosion in retrofit.",
                "The cost of poor communication is not just delay; it is the compounding of risk.",
                "Elite adaptive reuse is defined by data management, not just design aspiration."
            ],
            "sections": [
                {
                    "title": "Executive Summary: Solving the Retrofit Crisis",
                    "content": "The global adaptive reuse market is currently constrained by four primary pain points that drive CapEx variance and timeline slippage: Tech Complexity, Communication silos, Approval bottlenecks, and unpredictable Timelines. This guide provides a technical mandate for navigating these challenges using elite intervention models. Institutional developers are increasingly pivoting to retrofit over demolition, driven by 15-20% lower embodied carbon and significantly accelerated speed-to-market in supply-constrained urban cores. Root causes of project failure typically reside in the delta between legacy documentation and physical site reality, a gap that must be closed via early-stage technical audits and LiDAR-to-BIM conversion. Mitigation requires a transition from reactive problem-solving to proactive data-backed governance, ensuring that every design decision is grounded in measurable site constraints. KPIs for successful conversion include a 40% reduction in onsite RFIs and a 12% improvement in CapEx predictability compared to traditional heritage benchmarks."
                },
                {
                    "title": "Pain Point 1: Solving Tech Complexity (BIM, LiDAR, Structural)",
                    "content": "Problem: Tech complexity in adaptive reuse stems from the delta between legacy documentation and actual site conditions. Technical Root Causes: Undocumented structural modifications over decades, thermal bridging in heritage envelopes, and MEP routing constraints within restricted floor-to-ceiling heights. Quantified Impact: Unmanaged complexity leads to a 15-25% increase in change orders and a 28% RFI escalation rate during the CD phase. Mechanism: Misalignment between design intent and physical reality triggers late-stage field modifications, which are 3-5x more expensive than pre-construction adjustments. Mitigation: Mandatory 3D LiDAR point-cloud generation and LiDAR-to-BIM conversion prior to the Construction Documentation (CD) phase. Before: 18% change order risk from latent conditions. After: 8% change order variance via precision data. KPIs: 40% reduction in onsite structural RFIs. Micro-case: In a 1920s warehouse conversion in London, LiDAR scanning identified a 150mm floor slab variance that would have cost $120k in remedial leveling if discovered during fit-out."
                },
                {
                    "title": "Pain Point 2: Resolving Communication Breakdowns (OAC, RFI, Change Orders)",
                    "content": "Problem: Misalignment between Owner, Architect, and Contractor (OAC) typically triggers change-order inflation and sequencing conflicts. Technical Root Causes: Delayed feedback loops from approval authorities and fragmented Project Information Models (PIM). Quantified Impact: Poor communication adds 5-10% to total project CapEx and delays delivery by an average of 14 weeks. Mechanism: Asynchronous information flow leads to procurement errors and trade sequencing clashes in restricted heritage sites. Mitigation: Implementation of a centralized Project Information Model (PIM) and a structured coordination governance framework with 48-hour RFI response mandates. Before: 14-week communication breakdown delay. After: 4-week decision response cycle. KPIs: 25% faster decision-making cycles and 15% reduction in coordination-driven change orders. Micro-case: A heritage mill conversion utilized a digital RFI dashboard to resolve 85% of coordination issues within the 48-hour mandate, saving 6 weeks of idle trade time."
                },
                {
                    "title": "Pain Point 3: Accelerating Approvals (Zoning, Heritage, Compliance)",
                    "content": "Problem: Approval delays are driven by incomplete documentation regarding heritage preservation and change-of-use permissions. Technical Root Causes: Sequential zoning overlays and lack of early-stage fire/life-safety compliance audits. Quantified Impact: Approval bottlenecks can stall projects for 6-18 months, reducing project IRR by 350-500 basis points. Mechanism: Permit dependency chains create critical-path slippage when heritage boards request mid-stream design revisions. Mitigation: Parallel submission strategy combined with early engagement ('Pre-App') with planning authorities and comprehensive heritage envelope audits. Before: 11-month average approval cycle. After: 7-month approval cycle via precision documentation. KPIs: 16-week reduction in total permit acquisition time. Micro-case: By submitting heritage and environmental permits in parallel for a downtown retrofit, the developer shaved 4 months off the financing cost, saving $240k in interest carry."
                },
                {
                    "title": "Pain Point 4: Compressing Timelines (Surprises, Logistics, Abatement)",
                    "content": "Problem: Long timelines are primarily driven by unknown site conditions and hazardous material surprises during main works. Technical Root Causes: Asbestos/lead abatement and structural reinforcement surprises in heritage shells. Quantified Impact: Timeline slippage reduces project IRR by 2-5 points and increases construction financing costs by 12-15%. Mechanism: Discovery of hazardous materials during main trade works disrupts the entire sequencing chain. Mitigation: Risk-based buffer allocation (10-15%) and phased construction sequencing with 'Early Works' packages for abatement and structural reinforcement. Before: 26-month projected timeline for complex retrofit. After: 21-month delivery via early works packages. KPIs: 18% schedule compression. Micro-case: A phased abatement strategy in an industrial-to-office conversion allowed fit-out trades to commence 3 months early, resulting in a $450k early-tenant-move-in premium."
                },
                {
                    "title": "Financial Modeling & Investment Strategy",
                    "content": "Elite financial modeling for adaptive reuse must account for the 'Heritage Premium'—a 15-20% rental uplift typical for repositioned assets in prime urban locations. CapEx modeling breakdown: Structural reuse typically saves 30-40% on core costs but requires a 12-15% increase in MEP spend to accommodate heritage shell constraints. IRR sensitivity analysis indicates that a 3-month approval delay costs approximately 180 basis points in institutional financing charges. Investment Strategy: Leverage brownfield tax incentives and ESG-linked debt to offset initial audit costs. A comparison of Demolition vs Retrofit ROI often shows that while retrofit CapEx is 5-8% higher, the 20% faster speed-to-market and lower carbon footprint result in a superior 5-year IRR for institutional investors."
                },
                {
                    "title": "Risk Allocation & Contract Strategy",
                    "content": "Standard contract models often fail in adaptive reuse due to improper risk transfer regarding latent site conditions. Technical Intervention: Risk transfer matrix allocates 'Existing Condition' risk to the Owner while shifting 'Execution' and 'Sequencing' risk to the Contractor through GMP (Guaranteed Maximum Price) models. Comparison: Design-Build (DB) offers faster delivery but requires 15% higher contingency buffers; Construction Management (CM) at Risk provides greater transparency for heritage conversions. Insurance: Live-building retrofits require specialized 'Surrounding Property' and hazardous material liability coverage. Implementation of a structured contingency allocation (typical range 8-15%) reduces dispute volume by 35% by providing a clear mechanism for 'Discovery Phase' adjustments."
                },
                {
                    "title": "ESG & Urban Regeneration Impact",
                    "content": "Adaptive reuse is the primary lever for urban ESG performance. Embodied carbon comparison: Structural reuse saves an average of 650kg CO2/m2 compared to new build construction. Operational Energy: High-performance envelope retrofitting, including internal wall insulation and vacuum glazing, achieves 45% reduction in kWh/m2/year. Social Value: Brownfield regeneration creates a 3.5x multiplier effect on local economic activity through placemaking and Public-Private Partnership (PPP) leverage. Urban Regeneration: Strategic conversions of vacant Grade-B office assets into mixed-use hubs can revitalize declining urban cores, attracting high-value talent and increasing municipal tax revenue by 12-18% post-completion."
                },
                {
                    "title": "Performance Dashboard: Strategic Outcomes",
                    "content": "Performance Report: 1) Approval Cycle Reduction: 4 months saved via parallel submission. 2) Change Order Reduction: 12% decrease through LiDAR point-cloud audits. 3) RFI Volume Reduction: 40% via BIM-to-Field coordination. 4) Schedule Compression: 18% through early works abatement packages. 5) IRR Improvement: 420 bps through optimized financing and rental premium. 6) Asset Value Uplift: 28% post-repositioning. 7) CapEx Predictability: 15% variance reduction. 8) Embodied Carbon Savings: 65% vs new build GWP. Institutional Example: A 150,000 sq ft heritage mill conversion achieved 21-month delivery (vs 26-month baseline) with only 7.5% change order variance, resulting in a 24% project IRR."
                }
            ],
            "call_to_action": {
                "headline": "Ready to De-Risk Your Institutional Asset?",
                "description": "Our senior consulting methodology turns the four pain points of adaptive reuse into measurable competitive advantages through technical precision and data-backed governance.",
                "button_text": "Schedule a Technical Audit"
            }
        }
            "call_to_action": {
                "headline": "Ready to De-Risk Your Conversion?",
                "description": "Our methodology turns the four pain points into competitive advantages through technical precision and strategic governance.",
                "button_text": "Schedule a Technical Audit"
            }
        }

    def ensure_section_content(self, sections: List[Dict[str, str]], signals: Dict[str, str], firm_profile: Dict[str, Any]) -> List[Dict[str, str]]:
        while len(sections) < 9: sections.append({"title": f"Strategic Focus {len(sections)+1}", "content": ""})
        def is_thin(text: str) -> bool: return len(text.split()) < 250 # Increased threshold for elite density
        indices_to_fix = [i for i, s in enumerate(sections) if is_thin(s.get("content", ""))]
        if not indices_to_fix: return sections
        def regenerate_one(idx: int) -> Dict[str, str]:
            title = sections[idx].get("title")
            prompt = f"Senior expert analysis for '{title}' regarding '{signals.get('main_topic')}'. Write 700 words of technical, data-backed consulting content. No fluff. Include metrics and technical protocols."
            try:
                resp = requests.post(self.base_url, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": "sonar", "messages": [{"role": "user", "content": prompt}], "max_tokens": 1500, "temperature": 0.6}, timeout=45)
                if resp.status_code == 200:
                    new_content = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                    return {"title": title, "content": new_content}
            except Exception: pass
            return sections[idx]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_idx = {executor.submit(regenerate_one, i): i for i in indices_to_fix}
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                sections[idx] = future.result()
        return sections

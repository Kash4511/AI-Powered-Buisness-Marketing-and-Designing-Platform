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
        main_topic = signals.get('main_topic', 'Adaptive Reuse Guide')
        return f"""
You are a senior adaptive-reuse consultant with 20+ years of experience.
Generate a high-density, technical Executive Guide titled: "{main_topic}".

CRITICAL REQUIREMENTS:
1. NO FLUFF: Avoid "holistic approach", "actionable insights", "future-proofing". Use technical examples like "façade retention", "zoning overlay", "BIM integration", "MEP retrofit", "embodied carbon analysis".
2. METRICS: Include at least 15 measurable metrics (e.g., "% CapEx reduction", "NOI uplift", "kWh/m2/year", "GWP reduction").
3. AUDIENCE SEGMENTS (Technical Deep-Dives):
   - Commercial Clients: Demolition vs Retrofit ROI, tax incentives, vacancy mitigation.
   - Government Authorities: Urban regeneration, historic preservation compliance, PPP models.
   - Architects: Structural constraints, thermal bridging in heritage envelopes, BIM-to-Field.
   - Contractors: Site logistics in dense urban cores, hazardous material abatement, sequencing in live buildings.
4. 6 CHAPTERS: 
   - Chapter 1: Strategic Foundation (Economics & Vision)
   - Chapter 2: Market & Regulatory Framework (Zoning & Policy)
   - Chapter 3: Technical Framework (Structure & Systems)
   - Chapter 4: Implementation Roadmap (Phase 1-5 Execution)
   - Chapter 5: Risk & Governance (Legal & Operational Safeguards)
   - Chapter 6: Measurable Outcomes (KPIs & Final Delivery)

OUTPUT — Return ONLY valid JSON:
{{
  "title": "{main_topic}", 
  "summary": "80-120 words of high-level strategic overview.", 
  "outcome_statement": "Concrete value proposition (max 80 chars).",
  "key_insights": ["Insight 1", "Insight 2", "Insight 3", "Insight 4", "Insight 5"],
  "pull_quotes": ["Expert Quote 1", "Expert Quote 2", "Expert Quote 3"],
  "stats": {{ "s1v": "Val", "s1l": "Label", "s2v": "V", "s2l": "L", "s3v": "V", "s3l": "L", "s4v": "V", "s4l": "L", "s5v": "V", "s5l": "L", "s6v": "V", "s6l": "L", "s7v": "V", "s7l": "L", "s8v": "V", "s8l": "L", "s9v": "V", "s9l": "L" }},
  "commercial_analysis": "Technical deep-dive (150-200 words) for Commercial Clients...",
  "government_analysis": "Technical deep-dive (150-200 words) for Government Authorities...",
  "architect_analysis": "Technical deep-dive (150-200 words) for Architects...",
  "contractor_analysis": "Technical deep-dive (150-200 words) for Contractors...",
  "checklists": [ {{ "items": ["Item 1", "Item 2", "Item 3", "Item 4"] }}, {{ "items": ["I1", "I2", "I3", "I4"] }}, {{ "items": ["I1", "I2", "I3"] }} ],
  "info_cards": [ {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }} ],
  "callouts": [ {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }}, {{ "label": "L", "content": "C" }} ],
  "sections": [
    {{ "title": "Strategic Foundation", "content": "700-1000 words of technical analysis..." }},
    {{ "title": "Market & Regulatory Framework", "content": "700-1000 words of technical analysis..." }},
    {{ "title": "Technical Framework", "content": "700-1000 words of technical analysis..." }},
    {{ "title": "Implementation Roadmap", "content": "700-1000 words of technical analysis..." }},
    {{ "title": "Risk & Governance", "content": "700-1000 words of technical analysis..." }},
    {{ "title": "Measurable Outcomes", "content": "700-1000 words of technical analysis..." }}
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
            "commercial_analysis": "", "government_analysis": "", "architect_analysis": "", "contractor_analysis": "",
            "checklists": [], "info_cards": [], "callouts": [], "sections": [],
            "call_to_action": {"headline": "", "description": "", "button_text": ""},
        }
        if not isinstance(raw, dict): return out
        def ct(v: Any) -> str: return str(v).strip() if v else ""
        out["title"] = ct(raw.get("title"))
        out["summary"] = ct(raw.get("summary"))
        out["outcome_statement"] = ct(raw.get("outcome_statement"))
        out["commercial_analysis"] = ct(raw.get("commercial_analysis"))
        out["government_analysis"] = ct(raw.get("government_analysis"))
        out["architect_analysis"] = ct(raw.get("architect_analysis"))
        out["contractor_analysis"] = ct(raw.get("contractor_analysis"))
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
        if isinstance(cta, dict): out["call_to_action"] = {k: ct(cta.get(k)) for k in ["headline", "description", "button_text"]}
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
            while len(sections) < 10: sections.append({"title": f"Section {len(sections)+1}", "content": ""})
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
            
            main_title = str(ai_content.get("title") or f"{ua.get('main_topic','Adaptive Reuse')} Guide").strip()
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
                "coverSeriesLabel": "EXECUTIVE SERIES", "coverEyebrow": "STRATEGIC ANALYSIS",
                "coverHeadlineLine1": hl1, "coverHeadlineLine2": hl2, "coverHeadlineLine3": company,
                "coverTagline": ai_content.get("outcome_statement","")[:80],
                "stat1Value": "100%", "stat1Label": "PROFESSIONAL", "stat2Value": "AI", "stat2Label": "OPTIMISED", "stat3Value": year, "stat3Label": "EDITION",
                "sectionTitle1": "Introduction", "pageNumber2": "2", "termsHeadline": f"{hl1}: {hl2}", "termsParagraph1": ai_content.get("summary",""),
                "termsPullQuote": quo(0, "Strategy is execution."), "termsCopyright": f"© {year} {company}",
                "keyInsight1": ins(0), "keyInsight2": ins(1), "keyInsight3": ins(2), "keyInsight4": ins(3), "keyInsight5": ins(4),
                "sectionTitle2": "Contents", "pageNumber3": "3", "tocHeadlineLine1": "Strategic", "tocHeadlineLine2": "Roadmap",
                "tocItem1": st(0), "tocSub1": sc(0)[:120] + "...",
                "tocItem2": st(1), "tocSub2": sc(1)[:120] + "...",
                "tocItem3": st(2), "tocSub3": sc(2)[:120] + "...",
                "tocItem4": st(3), "tocSub4": sc(3)[:120] + "...",
                "tocItem5": st(4), "tocSub5": sc(4)[:120] + "...",
                "tocItem6": st(5), "tocSub6": sc(5)[:120] + "...",
                "chapter1Section": "CHAPTER 01", "chapter1Eyebrow": "STRATEGIC", "chapter1Title": st(0), "chapter1Intro": sc(0)[:220], "chapter1Body1": sc(0), "dropCap1": (sc(0)[:1] or "S").upper(),
                "chapter2Section": "CHAPTER 02", "chapter2Eyebrow": "REGULATORY", "chapter2Title": st(1), "chapter2Intro": sc(1)[:220], "chapter2Body1": sc(1), "dropCap2": (sc(1)[:1] or "O").upper(),
                "chapter3Section": "CHAPTER 03", "chapter3Eyebrow": "TECHNICAL", "chapter3Title": st(2), "chapter3Intro": sc(2)[:220], "chapter3Body1": sc(2), "dropCap3": (sc(2)[:1] or "I").upper(),
                "chapter4Section": "CHAPTER 04", "chapter4Eyebrow": "ROADMAP", "chapter4Title": st(3), "chapter4Intro": sc(3)[:220], "chapter4Body1": sc(3), "dropCap4": (sc(3)[:1] or "C").upper(),
                "chapter5Section": "CHAPTER 05", "chapter5Eyebrow": "RISK", "chapter5Title": st(4), "chapter5Intro": sc(4)[:220], "chapter5Body1": sc(4), "dropCap5": (sc(4)[:1] or "A").upper(),
                "chapter6Section": "CHAPTER 06", "chapter6Eyebrow": "OUTCOMES", "chapter6Title": st(5), "chapter6Intro": sc(5)[:220], "chapter6Body1": sc(5), "dropCap6": (sc(5)[:1] or "M").upper(),
                "imagePage4Url": img1, "imagePage5Url": img2, "imagePage6Url": img3,
                "imageCaption1": "Strategic Assessment", "imageCaption2": "Market Context", "imageCaption3": "Technical Audit",
                "callout1Title": ol(0, "KEY TAKEAWAY"), "callout1Body": oc(0, "Execution beats strategy."),
                "stat1v": sv("s1v", "85%"), "stat1l": sv("s1l", "Alignment"),
                "stat2v": sv("s2v", "2.4x"), "stat2l": sv("s2l", "Efficiency"),
                "ctaTitle": (ai_content.get("call_to_action") or {}).get("headline") or "Start Your Journey",
                "ctaBody": (ai_content.get("call_to_action") or {}).get("description") or "Ready to begin?",
                "ctaButtonText": (ai_content.get("call_to_action") or {}).get("button_text") or "Connect Now",
                "pageNumber4": "4", "pageNumber5": "5", "pageNumber6": "6", "pageNumber7": "7", "pageNumber8": "8", "pageNumber9": "9"
            }
            return v
        except Exception:
            logger.error(f"❌ Mapping Guard: {traceback.format_exc()}")
            return {"mainTitle": "Expert Guide"}

    def _build_fallback_content(self, signals: Dict[str, Any], fp: Dict[str, Any]) -> Dict[str, Any]:
        return {"title": "Adaptive Reuse Guide", "summary": "Strategic overview.", "sections": [{"title": "Foundation", "content": "Professional analysis..."}]}

    def ensure_section_content(self, sections: List[Dict[str, str]], signals: Dict[str, str], firm_profile: Dict[str, Any]) -> List[Dict[str, str]]:
        while len(sections) < 6: sections.append({"title": f"Strategic Focus {len(sections)+1}", "content": ""})
        def is_thin(text: str) -> bool: return len(text.split()) < 100
        indices_to_fix = [i for i, s in enumerate(sections) if is_thin(s.get("content", ""))]
        if not indices_to_fix: return sections
        def regenerate_one(idx: int) -> Dict[str, str]:
            title = sections[idx].get("title")
            prompt = f"Senior expert analysis for '{title}' regarding '{signals.get('main_topic')}'. Write 700 words. Technical tone."
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

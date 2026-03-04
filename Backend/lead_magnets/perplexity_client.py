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
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY is missing. Cannot generate content.")
        
        prompt = self._create_content_prompt(signals, firm_profile)
        system_prompt = (
            "You are a senior institutional consultant. "
            "Output ONLY valid JSON. "
            "STRICT REQUIREMENTS:\n"
            "1. NO markdown code fences (do not use ```json or ```).\n"
            "2. NO repetition: Every chapter must have unique, dense technical analysis.\n"
            "3. ZERO placeholders: No 'pending audit' or 'TBD' metrics.\n"
            "4. Institutional depth: Minimum 300 words per strategic section.\n"
        )

        def attempt_generation(current_prompt: str, is_retry: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
            try:
                logger.info(f"🚀 AI Generation Attempt {'Retry' if is_retry else '1'}")
                response = requests.post(
                    self.base_url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Accept": "application/json"},
                    json={
                        "model": "sonar",
                        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": current_prompt}],
                        "max_tokens": 4000,
                        "temperature": 0.2,
                    },
                    timeout=90,
                )
                if response.status_code != 200:
                    raise ValueError(f"AI API Error: {response.status_code}")
                
                raw = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                if not raw:
                    raise ValueError("Empty content from AI")

                sanitized = self._extract_json(raw)
                data = json.loads(sanitized)
                
                # 1. STRICT VALIDATION GATE
                self.validate_ai_structure(data)
                
                # 2. STRICT NORMALIZATION LAYER
                normalized = self.normalize_ai_output(data)
                
                return normalized, raw
            except ValueError as ve:
                # Validation failure or API status error -> immediately bubble up, do NOT catch in transport logic
                logger.error(f"❌ Validation/API Failure: {str(ve)}")
                raise
            except Exception as e:
                # Transport/Network errors -> logged and allowed to return None for retry
                logger.error(f"⚠️ AI Transport Error: {str(e)}")
                if is_retry: raise e
                return None, None

        # Attempt generation with strict validation
        result, failed_text = attempt_generation(prompt)
        if result:
            logger.info("✅ Deterministic AI generation successful")
            return result
        
        # One retry attempt ONLY for transport errors (result was None)
        # Validation errors already raised and exited above.
        logger.info("🔄 Transport failure detected. Attempting one-time retry...")
        result, _ = attempt_generation(prompt, is_retry=True)
        
        if not result:
            raise ValueError("AI generation failed after retry due to transport errors.")
            
        return result

    def validate_ai_structure(self, data: Dict[str, Any]):
        """Strict structural enforcement gate for institutional-grade content."""
        if not isinstance(data, dict):
            raise ValueError("AI response is not a valid JSON object")
            
        # 1. ROOT FIELD ENFORCEMENT
        required_root_keys = [
            "title", "summary", "outcome_statement", 
            "commercial_analysis", "government_analysis", 
            "architect_analysis", "contractor_analysis",
            "sections", "key_insights", "pull_quotes", 
            "info_cards", "callouts", "stats", "checklists"
        ]
        for key in required_root_keys:
            if key not in data or not data[key]:
                raise ValueError(f"AI response missing or empty required root key: {key}")

        # 2. EXACT COUNT ENFORCEMENT (Aligns with Template.html requirements)
        counts = {
            "sections": 9,
            "key_insights": 5,
            "pull_quotes": 3,
            "callouts": 5,
            "info_cards": 7,
            "checklists": 3
        }
        for key, expected in counts.items():
            actual = len(data.get(key, []))
            if actual != expected:
                raise ValueError(f"Structural Mismatch: '{key}' must have exactly {expected} items. Got {actual}.")

        # 3. STATS COUNT ENFORCEMENT (Exactly 9 pairs: s1v-s9v, s1l-s9l)
        stats = data.get("stats", {})
        for i in range(1, 10):
            if f"s{i}v" not in stats or not str(stats[f"s{i}v"]).strip():
                raise ValueError(f"Missing required stat value: s{i}v")
            if f"s{i}l" not in stats or not str(stats[f"s{i}l"]).strip():
                raise ValueError(f"Missing required stat label: s{i}l")

        # 4. SECTION DEPTH & QUALITY ENFORCEMENT
        seen_paragraphs = set()
        for i, section in enumerate(data["sections"]):
            required_fields = ["chapter_title", "chapter_subtitle", "opening_paragraph"]
            for field in required_fields:
                val = str(section.get(field, "")).strip()
                if not val:
                    raise ValueError(f"Section {i+1} missing required field: {field}")
                
                if field == "opening_paragraph":
                    # Minimum 200 words per strategic chapter
                    word_count = len(val.split())
                    if word_count < 200:
                        raise ValueError(f"Section {i+1} too short ({word_count} words). Minimum 200 required.")
                    
                    # Placeholder detection
                    PLACEHOLDERS = ["pending final audit", "TBD", "insert data here", "strategic transformation requires a holistic"]
                    if any(p.lower() in val.lower() for p in PLACEHOLDERS):
                        raise ValueError(f"Section {i+1} contains invalid placeholder text.")
                    
                    # Repetition detection (signature-based)
                    signature = val[:100].lower()
                    if signature in seen_paragraphs:
                        raise ValueError(f"Section {i+1} contains repetitive content from a previous section.")
                    seen_paragraphs.add(signature)

    def _create_content_prompt(self, signals: Dict[str, str], firm_profile: Dict[str, Any]) -> str:
        main_topic = signals.get('main_topic', 'Adaptive Reuse Executive Guide')
        return f"""
Act as a Senior Institutional Adaptive-Reuse Consultant for Global Asset Managers. 
Generate an elite, 13-page Technical Advisory Report for '{main_topic}'.

The document must read like a McKinsey, BCG, or institutional advisory report. No fluff. No motivational filler. Use formal, technical, and precise language. Use positive, solution-oriented terminology. Focus on capabilities, strategic advantages, and outcomes. NEVER use the term "pain points" or emphasize negative framing.

DOCUMENT STRUCTURE (MANDATORY 9 SECTIONS):
1.  Accelerating Asset Value through Strategic Transformation.
2. TECHNICAL PRECISION & BIM INTEGRATION (Digital Twins, Structural Optimization, Envelope Excellence).
3. INSTITUTIONAL SYNERGY & COLLABORATION (Unified OAC Protocols, RFI Efficiency, Seamless Stakeholder Alignment).
4. REGULATORY AGILITY & POLICY LEVERAGE (Expedited Compliance, Zoning Unlock, Heritage Value Capture).
5.  TIMELINE ACCELERATION & OPERATIONAL EXCELLENCE (Phased Abatement, Early Works Sequencing, Critical Path Optimization).
6.  IRR Maximization, CapEx Efficiency, and Long-Term Asset Appreciation.
7.: Proactive GMP Frameworks, CM-at-Risk, Latent Condition Management.
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
    {{
      "chapter_title": "EXECUTIVE SUMMARY",
      "chapter_subtitle": "Maximizing Asset Potential through Strategic Transformation",
      "opening_paragraph": "150 words of elite institutional overview...",
      "root_causes": ["Technical Precision", "Collaborative Synergy", "Regulatory Agility"],
      "quantified_impact": "Proactive retrofit management can improve project IRR by 400-600 basis points.",
      "intervention_framework": "Transition from reactive problem-solving to proactive data-backed governance.",
      "benchmark_case": "Metropolitan Retrofit: 40% faster speed-to-market.",
      "kpis": [{{ "before": "18% change order variance", "after": "7% precision" }}],
      "comparison_table": [{{ "factor": "CapEx", "challenge": "Audit Investment", "response": "18% variance reduction" }}]
    }},
    {{
      "chapter_title": "STRATEGIC ADVANTAGE 1: TECHNICAL PRECISION",
      "chapter_subtitle": "LiDAR-to-BIM Asset Intelligence",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{{ "before": "...", "after": "..." }}],
      "comparison_table": [{{ "factor": "...", "challenge": "...", "response": "..." }}]
    }},
    {{
      "chapter_title": "STRATEGIC ADVANTAGE 2: INSTITUTIONAL SYNERGY",
      "chapter_subtitle": "OAC Protocols & RFI Efficiency",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{{ "before": "...", "after": "..." }}],
      "comparison_table": [{{ "factor": "...", "challenge": "...", "response": "..." }}]
    }},
    {{
      "chapter_title": "STRATEGIC ADVANTAGE 3: REGULATORY AGILITY",
      "chapter_subtitle": "Heritage Compliance & Zoning Unlock",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{{ "before": "...", "after": "..." }}],
      "comparison_table": [{{ "factor": "...", "challenge": "...", "response": "..." }}]
    }},
    {{
      "chapter_title": "STRATEGIC ADVANTAGE 4: TIMELINE ACCELERATION",
      "chapter_subtitle": "Early Works Sequencing",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{{ "before": "...", "after": "..." }}],
      "comparison_table": [{{ "factor": "...", "challenge": "...", "response": "..." }}]
    }},
    {{
      "chapter_title": "FINANCIAL PERFORMANCE MODELING",
      "chapter_subtitle": "IRR Sensitivity & Asset Appreciation",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{{ "before": "...", "after": "..." }}],
      "comparison_table": [{{ "factor": "...", "challenge": "...", "response": "..." }}]
    }},
    {{
      "chapter_title": "GOVERNANCE & RISK TRANSFER",
      "chapter_subtitle": "Contractual Indemnity & Latent Conditions",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{{ "before": "...", "after": "..." }}],
      "comparison_table": [{{ "factor": "...", "challenge": "...", "response": "..." }}]
    }},
    {{
      "chapter_title": "ESG LEADERSHIP",
      "chapter_subtitle": "Embodied Carbon & Social Multipliers",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{{ "before": "...", "after": "..." }}],
      "comparison_table": [{{ "factor": "...", "challenge": "...", "response": "..." }}]
    }},
    {{
      "chapter_title": "STRATEGIC PERFORMANCE DASHBOARD",
      "chapter_subtitle": "Quantified Strategic Outcomes",
      "opening_paragraph": "...",
      "root_causes": ["...", "...", "..."],
      "quantified_impact": "...",
      "intervention_framework": "...",
      "benchmark_case": "...",
      "kpis": [{{ "before": "...", "after": "..." }}],
      "comparison_table": [{{ "factor": "...", "challenge": "...", "response": "..." }}]
    }}
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
        if not isinstance(raw, dict):
            raise ValueError("AI output is not a valid JSON object")
            
        def ct(v: Any) -> str: 
            val = str(v).strip() if v else ""
            if not val: raise ValueError("Empty required field detected in AI output")
            return val

        out: Dict[str, Any] = {
            "title": ct(raw.get("title")), 
            "summary": ct(raw.get("summary")), 
            "outcome_statement": ct(raw.get("outcome_statement")),
            "commercial_analysis": ct(raw.get("commercial_analysis")), 
            "government_analysis": ct(raw.get("government_analysis")), 
            "architect_analysis": ct(raw.get("architect_analysis")), 
            "contractor_analysis": ct(raw.get("contractor_analysis")),
            "key_insights": [ct(ki) for ki in raw.get("key_insights", []) if ki], 
            "pull_quotes": [ct(q) for q in raw.get("pull_quotes", []) if q], 
            "stats": {k: ct(v) for k, v in raw.get("stats", {}).items()},
            "checklists": [], 
            "info_cards": [], 
            "callouts": [], 
            "sections": [],
            "call_to_action": {
                "headline": ct(raw.get("call_to_action", {}).get("headline")), 
                "description": ct(raw.get("call_to_action", {}).get("description")), 
                "button_text": ct(raw.get("call_to_action", {}).get("button_text"))
            },
        }

        for cl in raw.get("checklists", []):
            if isinstance(cl, dict): out["checklists"].append({"items": [ct(i) for i in cl.get("items", []) if i]})
        for card in raw.get("info_cards", []):
            if isinstance(card, dict): out["info_cards"].append({"label": ct(card.get("label")), "content": ct(card.get("content"))})
        for co in raw.get("callouts", []):
            if isinstance(co, dict): out["callouts"].append({"label": ct(co.get("label")), "content": ct(co.get("content"))})
        
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
                
        return out

    def map_to_template_vars(self, ai_content: Dict[str, Any], firm_profile: Optional[Dict[str, Any]] = None,
                             user_answers: Optional[Dict[str, Any]] = None, architectural_images: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            fp = firm_profile or {}
            ua = user_answers or {}
            imgs = architectural_images or []
            
            # 1. MANDATORY IMAGE CHECK (No fallbacks allowed)
            if len(imgs) < 1:
                raise ValueError("Missing required architectural image 1 for lead magnet generation.")
            
            img1 = imgs[0]
            img2 = imgs[1] if len(imgs) >= 2 else img1
            img3 = imgs[2] if len(imgs) >= 3 else img1

            sections = ai_content["sections"]
            
            def st(i): 
                val = str(sections[i]["chapter_title"]).strip()
                if not val: raise ValueError(f"Section {i+1} title is empty")
                return val
                
            def sc(i): 
                val = str(sections[i]["opening_paragraph"]).strip()
                if not val: raise ValueError(f"Section {i+1} content is empty")
                return val

            stats = ai_content["stats"]
            def sv(k): 
                val = str(stats[k]).strip()
                if not val: raise ValueError(f"Missing stat value for {k}")
                return val

            insights = ai_content["key_insights"]
            quotes = ai_content["pull_quotes"]
            cards = ai_content["info_cards"]
            callouts = ai_content["callouts"]

            def ins(i): return str(insights[i])
            def quo(i): return str(quotes[i])
            def cl(i): return str(cards[i]["label"])
            def cc(i): return str(cards[i]["content"])
            def ol(i): return str(callouts[i]["label"])
            def oc(i): return str(callouts[i]["content"])
            
            def chk(i, j): 
                val = str(ai_content["checklists"][i]["items"][j]).strip()
                if not val: raise ValueError(f"Empty checklist item at {i+1}:{j+1}")
                return val
            
            main_title = str(ai_content["title"]).strip()
            if not main_title: raise ValueError("Document title is empty")
            
            hl_parts = main_title.split(":", 1)
            hl1 = hl_parts[0].strip()
            hl2 = hl_parts[1].strip() if len(hl_parts) > 1 else "Strategic Advisory"
            
            year = str(datetime.now().year)
            company = str(fp["firm_name"]).strip()
            if not company: raise ValueError("Firm name is missing in profile")
            
            email = str(fp["work_email"]).strip()
            phone = str(fp["phone_number"]).strip()
            website = str(fp["firm_website"]).strip()
            primary = str(fp["primary_brand_color"]).strip()
            if not primary: raise ValueError("Primary brand color is missing in firm profile")
            
            v = {
                "mainTitle": main_title, "documentTitle": main_title.upper(), "documentSubtitle": ai_content["summary"],
                "companyName": company, "emailAddress": email, "phoneNumber": phone, "website": website, "footerText": f"© {year} {company}",
                "primaryColor": primary, "secondaryColor": fp.get("secondary_brand_color","#B8860B"),
                "tertiaryColor": "#1E3A5F", "accentColor": "#4F7A8B", "creamColor": "#F7F4EF", "inkColor": "#1A1A1A", "ruleColor": "#DDDDDD",
                "commercialAnalysis": ai_content["commercial_analysis"],
                "governmentAnalysis": ai_content["government_analysis"],
                "architectAnalysis": ai_content["architect_analysis"],
                "contractorAnalysis": ai_content["contractor_analysis"],
                "coverBrand": company.upper(),
                "coverAudience": "EXECUTIVE SERIES",
                "coverTitleBold": hl1.upper(),
                "coverTitleItalic": hl2,
                "coverFooterLeft": f"© {year} {company}",
                "coverFooterRight": "STRATEGIC ANALYSIS",
                "coverTagline": ai_content["outcome_statement"][:80],
                "stat1Value": sv("s1v"), "stat1Label": sv("s1l"), "stat2Value": sv("s2v"), "stat2Label": sv("s2l"), "stat3Value": sv("s3v"), "stat3Label": sv("s3l"),
                "sectionTitle1": "Introduction", "pageNumber2": "2", "termsHeadline": f"{hl1}: {hl2}", "termsParagraph1": ai_content["summary"],
                "termsPullQuote": quo(0), "termsCopyright": f"© {year} {company}",
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
                "chapter1Section": "CHAPTER 01", "chapter1Eyebrow": "EXECUTIVE", "chapter1Title": st(0), "chapter1Intro": sc(0)[:220], "chapter1Body1": sc(0), "dropCap1": sc(0)[:1].upper(),
                "chapter2Section": "CHAPTER 02", "chapter2Eyebrow": "TECHNOLOGY", "chapter2Title": st(1), "chapter2Intro": sc(1)[:220], "chapter2Body1": sc(1), "dropCap2": sc(1)[:1].upper(),
                "chapter3Section": "CHAPTER 03", "chapter3Eyebrow": "COMMUNICATION", "chapter3Title": st(2), "chapter3Intro": sc(2)[:220], "chapter3Body1": sc(2), "dropCap3": sc(2)[:1].upper(),
                "chapter4Section": "CHAPTER 04", "chapter4Eyebrow": "APPROVALS", "chapter4Title": st(3), "chapter4Intro": sc(3)[:220], "chapter4Body1": sc(3), "dropCap4": sc(3)[:1].upper(),
                "chapter5Section": "CHAPTER 05", "chapter5Eyebrow": "TIMELINES", "chapter5Title": st(4), "chapter5Intro": sc(4)[:220], "chapter5Body1": sc(4), "dropCap5": sc(4)[:1].upper(),
                "chapter6Section": "CHAPTER 06", "chapter6Eyebrow": "FINANCIAL", "chapter6Title": st(5), "chapter6Intro": sc(5)[:220], "chapter6Body1": sc(5), "dropCap6": sc(5)[:1].upper(),
                "chapter7Section": "CHAPTER 07", "chapter7Eyebrow": "RISK", "chapter7Title": st(6), "chapter7Intro": sc(6)[:220], "chapter7Body1": sc(6), "dropCap7": sc(6)[:1].upper(),
                "chapter8Section": "CHAPTER 08", "chapter8Eyebrow": "ESG", "chapter8Title": st(7), "chapter8Intro": sc(7)[:220], "chapter8Body1": sc(7), "dropCap8": sc(7)[:1].upper(),
                "chapter9Section": "CHAPTER 09", "chapter9Eyebrow": "OUTCOMES", "chapter9Title": st(8), "chapter9Intro": sc(8)[:220], "chapter9Body1": sc(8), "dropCap9": sc(8)[:1].upper(),
                "imagePage4Url": img1, "imagePage5Url": img2, "imagePage6Url": img3,
                "imageCaption1": "Strategic Assessment", "imageCaption2": "Market Context", "imageCaption3": "Technical Audit",
                "callout1Title": ol(0), "callout1Body": oc(0),
                "callout2Title": ol(1), "callout2Body": oc(1),
                "callout3Title": ol(2), "callout3Body": oc(2),
                "callout4Title": ol(3), "callout4Body": oc(3),
                "callout5Title": ol(4), "callout5Body": oc(4),
                "tradeoffsTitle": "Market Trade-offs",
                "tradeoff1Term": cl(0), "tradeoff1Desc": cc(0),
                "tradeoff2Term": cl(1), "tradeoff2Desc": cc(1),
                "tradeoff3Term": cl(2), "tradeoff3Desc": cc(2),
                "tradeoff4Term": cl(3), "tradeoff4Desc": cc(3),
                "tradeoff5Term": cl(4), "tradeoff5Desc": cc(4),
                "phase1Title": cl(5), "phase1Desc": cc(5),
                "phase2Title": cl(6), "phase2Desc": cc(6),
                "caseStudy1Title": "Institutional Focus", "caseStudy1Desc": "Technical cause-and-effect analysis.", "caseStudy1Result": "Measurable IRR upside.",
                "caseStudy2Title": "Regulatory Impact", "caseStudy2Desc": "Compliance and sequencing optimization.", "caseStudy2Result": "Accelerated approval cycles.",
                "engagementMethodsTitle": "Strategic Methodology",
                "method1Phase": "Audit", "method1Desc": chk(0, 0),
                "method2Phase": "Design", "method2Desc": chk(0, 1),
                "method3Phase": "Abatement", "method3Desc": chk(1, 0),
                "method4Phase": "Systems", "method4Desc": chk(1, 1),
                "method5Phase": "Delivery", "method5Desc": chk(2, 0),
                "ctaIntro1": "The transition from legacy asset to high-performance building requires technical precision and strategic vision.",
                "ctaIntro2": "Our consulting methodology ensures that every project meets commercial ROI, regulatory requirements, and sustainability goals.",
                "ctaEyebrow": "NEXT STEPS",
                "contactLabel1": "EMAIL", "contactValue1": email,
                "contactLabel2": "PHONE", "contactValue2": phone,
                "contactLabel3": "WEBSITE", "contactValue3": website.replace("https://","").replace("http://",""),
                "stat1v": sv("s1v"), "stat1l": sv("s1l"),
                "stat2v": sv("s2v"), "stat2l": sv("s2l"),
                "ctaTitle": ai_content["call_to_action"]["headline"],
                "ctaBody": ai_content["call_to_action"]["description"],
                "ctaButtonText": ai_content["call_to_action"]["button_text"],
                "backCoverBrand": company.upper(),
                "backCoverTitle": main_title.upper(),
                "backCoverSub": "EXECUTIVE STRATEGY SERIES",
                "backCoverYear": year,
                "commercialAnalysis": ai_content["commercial_analysis"],
                "governmentAnalysis": ai_content["government_analysis"],
                "architectAnalysis": ai_content["architect_analysis"],
                "contractorAnalysis": ai_content["contractor_analysis"],
                "pageNumber4": "4", "pageNumber5": "5", "pageNumber6": "6", "pageNumber7": "7", "pageNumber8": "8", "pageNumber9": "9",
                "pageNumber10": "10", "pageNumber11": "11", "pageNumber12": "12"
            }
            return v
        except Exception as e:
            logger.error(f"❌ Mapping Guard: {traceback.format_exc()}")
            raise ValueError(f"Template mapping failed: {str(e)}")

    def _build_fallback_content(self, signals: Dict[str, Any], fp: Dict[str, Any]) -> Dict[str, Any]:
        """Disabled fallback logic. Fail loudly if AI generation fails."""
        raise ValueError("AI Generation failed and fallback is disabled.")

    def ensure_section_content(self, sections: List[Dict[str, Any]], signals: Dict[str, str], firm_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        # NO PADDING: Only render what AI provides.
        # Repetition and placeholder detection is handled by validate_ai_structure.
        return sections

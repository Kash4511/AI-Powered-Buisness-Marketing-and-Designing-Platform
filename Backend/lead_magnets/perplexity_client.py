"""
perplexity_client.py — Definitive version aligned to magazine-template-v5.html

ROOT CAUSE FIXES vs old broken version:
  1. max_tokens 1200 → 4000   (old value truncated JSON after ~3 sections)
  2. timeout 25s → 60s        (old value caused blank pages 6-13)
  3. Prompt now requests 10 sections + all supporting arrays (quotes, stats, cards, callouts, checklists)
  4. normalize_ai_output now extracts pull_quotes / stats / checklists / info_cards / callouts
  5. map_to_template_vars now populates EVERY {{variable}} in all 14 pages (200+ vars)
  6. ensure_section_content pads to 10 sections and parallel-regenerates thin ones
"""

import os
from pathlib import Path
import json
import requests
import re
import logging
import concurrent.futures
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

logger = logging.getLogger(__name__)


class PerplexityClient:
    """Client for Perplexity AI — generates all content for lead-magnet PDFs."""

    # ─────────────────────────────────────────────────────────────────────────
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

    # ── Signal helpers ────────────────────────────────────────────────────────

    def _is_meaningful(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, list):
            return any(self._is_meaningful(i) for i in value)
        v = str(value).strip()
        if len(v) < 2:
            return False
        FILLERS = {"test","testing","none","n/a","na","null","empty","ok","yes","no",
                   "placeholder","asdf","qwerty","lorem","ipsum","...","h","ok.",".","–"}
        if v.lower() in FILLERS:
            return False
        if not re.search(r'[A-Za-z0-9]', v):
            return False
        if len(v) > 4 and len(set(v.lower())) <= 2:
            return False
        return True

    def interpret_field(self, field_value: Any) -> str:
        if not self._is_meaningful(field_value):
            return "INFER_FROM_CONTEXT"
        if isinstance(field_value, list):
            cleaned = ", ".join(str(x).strip() for x in field_value if str(x).strip())
        else:
            cleaned = " ".join(str(field_value).split())
        return "INFER_FROM_CONTEXT" if len(cleaned) < 2 else f"REINTERPRET: {cleaned}"

    def get_semantic_signals(self, user_answers: Dict[str, Any]) -> Dict[str, str]:
        return {k: self.interpret_field(v) for k, v in user_answers.items()}

    # ── Main AI generation call ───────────────────────────────────────────────

    def generate_lead_magnet_json(
        self,
        signals: Dict[str, str],
        firm_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise Exception("PERPLEXITY_API_KEY is not configured")

        inferred      = [k for k, v in signals.items() if v == "INFER_FROM_CONTEXT"]
        reinterpreted = [k for k, v in signals.items() if v.startswith("REINTERPRET")]
        logger.info(f"🚀 Generating content (60s / 4000 tokens) | Inferred: {inferred} | Reinterpreted: {reinterpreted}")

        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a senior professional strategist. "
                                "Output ONLY valid JSON. No markdown fences. No commentary."
                            ),
                        },
                        {
                            "role": "user",
                            "content": self._create_content_prompt(signals, firm_profile),
                        },
                    ],
                    "max_tokens": 4000,   # ← CRITICAL FIX: was 1200
                    "temperature": 0.7,
                },
                timeout=60,              # ← CRITICAL FIX: was 25
            )
        except requests.exceptions.Timeout:
            raise Exception("AI content generation timed out (60 s).")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Perplexity API network error: {e}")

        if response.status_code != 200:
            raise Exception(f"Perplexity API {response.status_code}: {response.text}")

        raw = (
            response.json()
            .get('choices', [{}])[0]
            .get('message', {})
            .get('content', '')
        )
        cleaned = self._extract_json_from_markdown(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parse failed: {e}\nRAW (first 600): {repr(raw[:600])}")
            raise Exception("Invalid JSON returned from Perplexity API.")

    # ── Prompt ────────────────────────────────────────────────────────────────

    def _create_content_prompt(
        self, signals: Dict[str, str], firm_profile: Dict[str, Any]
    ) -> str:
        """
        Engineered to return every data structure the template needs.
        10 sections × ~180 words ≈ 1 800 words body.
        Supporting arrays ≈ 600 tokens.  Total budget ≤ 4 000 tokens.
        """
        return f"""
You are a senior expert content strategist. Generate a COMPLETE professional Lead Magnet.

RULES:
1. INFER_FROM_CONTEXT signals → synthesise from Topic + Audience.
2. REINTERPRET: [text] signals → professionalize and expand, never copy verbatim.
3. NEVER output empty strings, placeholders, or "…" filler.
4. Output ONLY valid JSON. No markdown. No commentary.
5. Every "content" field MUST be 150-220 words of full professional paragraphs.
6. You MUST produce ALL 10 sections — do not stop early.

SIGNALS:
  Lead Magnet Type : {signals.get('lead_magnet_type', 'Expert Report')}
  Main Topic       : {signals.get('main_topic',        'Professional Strategy')}
  Target Audience  : {signals.get('target_audience',   'Industry Leaders')}
  Pain Points      : {signals.get('audience_pain_points','Efficiency and Growth')}
  Desired Outcome  : {signals.get('desired_outcome',   'INFER_FROM_CONTEXT')}
  Call to Action   : {signals.get('call_to_action',    'INFER_FROM_CONTEXT')}
  Firm             : {firm_profile.get('firm_name',    'Expert Firm')}

OUTPUT — return this exact JSON structure, fully populated:
{{
  "title": "Compelling professional title",
  "summary": "Executive summary 60-80 words",
  "outcome_statement": "Concrete value proposition (one sentence)",
  "key_insights": [
    "Insight 1 — one strong sentence",
    "Insight 2",
    "Insight 3",
    "Insight 4",
    "Insight 5"
  ],
  "pull_quotes": [
    "Memorable quote 1 (15-25 words)",
    "Memorable quote 2 (15-25 words)",
    "Memorable quote 3 (15-25 words)"
  ],
  "stats": {{
    "s1v": "85%",  "s1l": "stat label 1",
    "s2v": "2.4x", "s2l": "stat label 2",
    "s3v": "10k+", "s3l": "stat label 3",
    "s4v": "3x",   "s4l": "stat label 4",
    "s5v": "67%",  "s5l": "stat label 5",
    "s6v": "92%",  "s6l": "stat label 6",
    "s7v": "40%",  "s7l": "stat label 7",
    "s8v": "5x",   "s8l": "stat label 8",
    "s9v": "98%",  "s9l": "stat label 9"
  }},
  "checklists": [
    {{ "items": ["Action 1", "Action 2", "Action 3", "Action 4"] }},
    {{ "items": ["Step 1",   "Step 2",   "Step 3",   "Step 4"  ] }},
    {{ "items": ["Result 1", "Result 2", "Result 3"            ] }}
  ],
  "info_cards": [
    {{ "label": "CARD LABEL 1", "content": "2-3 sentence professional insight." }},
    {{ "label": "CARD LABEL 2", "content": "2-3 sentence professional insight." }},
    {{ "label": "CARD LABEL 3", "content": "2-3 sentence professional insight." }},
    {{ "label": "CARD LABEL 4", "content": "2-3 sentence professional insight." }},
    {{ "label": "CARD LABEL 5", "content": "2-3 sentence professional insight." }},
    {{ "label": "CARD LABEL 6", "content": "2-3 sentence professional insight." }},
    {{ "label": "CARD LABEL 7", "content": "2-3 sentence professional insight." }}
  ],
  "callouts": [
    {{ "label": "KEY TAKEAWAY",  "content": "One powerful actionable sentence." }},
    {{ "label": "PRO TIP",       "content": "One powerful actionable sentence." }},
    {{ "label": "EXPERT NOTE",   "content": "One powerful actionable sentence." }},
    {{ "label": "INSIGHT",       "content": "One powerful actionable sentence." }},
    {{ "label": "CRITICAL POINT","content": "One powerful actionable sentence." }}
  ],
  "sections": [
    {{ "title": "Section 1 Title",  "content": "150-220 word professional paragraph…" }},
    {{ "title": "Section 2 Title",  "content": "150-220 word professional paragraph…" }},
    {{ "title": "Section 3 Title",  "content": "150-220 word professional paragraph…" }},
    {{ "title": "Section 4 Title",  "content": "150-220 word professional paragraph…" }},
    {{ "title": "Section 5 Title",  "content": "150-220 word professional paragraph…" }},
    {{ "title": "Section 6 Title",  "content": "150-220 word professional paragraph…" }},
    {{ "title": "Section 7 Title",  "content": "150-220 word professional paragraph…" }},
    {{ "title": "Section 8 Title",  "content": "150-220 word professional paragraph…" }},
    {{ "title": "Section 9 Title",  "content": "150-220 word professional paragraph…" }},
    {{ "title": "Section 10 Title", "content": "150-220 word professional paragraph…" }}
  ],
  "call_to_action": {{
    "headline":    "High-converting CTA headline",
    "description": "2-3 sentence reasoning for the next step",
    "button_text": "Action verb phrase"
  }}
}}
""".strip()

    # ── JSON repair ───────────────────────────────────────────────────────────

    def _extract_json_from_markdown(self, text: str) -> str:
        if not text:
            return ""
        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if m:
            text = m.group(1).strip()
        a, b = text.find('{'), text.rfind('}')
        if a == -1 or b == -1 or b <= a:
            return text.strip()
        js = text[a:b + 1].strip()
        try:
            json.loads(js)
            return js
        except json.JSONDecodeError:
            js = re.sub(r',\s*$', '', js)
            js += ']' * max(0, js.count('[') - js.count(']'))
            js += '}' * max(0, js.count('{') - js.count('}'))
            return js

    # ── Normalisation ─────────────────────────────────────────────────────────

    def normalize_ai_output(self, raw: Any) -> Dict[str, Any]:
        """
        Structural safety layer.
        Extracts and guarantees all arrays the template needs:
        sections, pull_quotes, stats, checklists, info_cards, callouts.
        """
        out: Dict[str, Any] = {
            "title": "", "summary": "", "outcome_statement": "",
            "key_insights": [], "pull_quotes": [], "stats": {},
            "checklists": [], "info_cards": [], "callouts": [],
            "sections": [],
            "call_to_action": {"headline": "", "description": "", "button_text": ""},
        }

        def ct(v: Any) -> str:
            if v is None:
                return ""
            if isinstance(v, list):
                v = " ".join(ct(i) for i in v if i)
            elif isinstance(v, dict):
                v = " ".join(f"{k}: {ct(val)}" for k, val in v.items())
            s = str(v).strip()
            s = re.sub(r'#+\s*', '', s)
            s = re.sub(r'\*+', '', s)
            s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s)
            s = re.sub(r'\n?\|.*\|(\n\|.*\|)*', '', s)
            return s

        def extract_sections(data: Any) -> List[Dict[str, str]]:
            secs: List[Dict[str, str]] = []
            if isinstance(data, list):
                for item in data:
                    secs.extend(extract_sections(item))
            elif isinstance(data, dict):
                if "title" in data or "content" in data:
                    secs.append({"title": ct(data.get("title", "")),
                                 "content": ct(data.get("content", ""))})
                    for sub in data.get("subsections", []):
                        secs.append({"title": ct(sub.get("title", "")),
                                     "content": ct(sub.get("content", ""))})
                else:
                    for k, v in data.items():
                        if k in ("sections", "contents", "items"):
                            secs.extend(extract_sections(v))
                        elif isinstance(v, (str, list, dict)):
                            secs.append({"title": ct(k), "content": ct(v)})
            return secs

        if isinstance(raw, dict):
            out["title"]             = ct(raw.get("title", ""))
            out["summary"]           = ct(raw.get("summary", ""))
            out["outcome_statement"] = ct(raw.get("outcome_statement", ""))

            for ki in (raw.get("key_insights") or []):
                if ki: out["key_insights"].append(ct(ki))

            for q in (raw.get("pull_quotes") or []):
                if q: out["pull_quotes"].append(ct(q))

            st = raw.get("stats", {})
            if isinstance(st, dict):
                out["stats"] = {k: ct(v) for k, v in st.items()}

            for cl in (raw.get("checklists") or []):
                if isinstance(cl, dict):
                    out["checklists"].append(
                        {"items": [ct(i) for i in cl.get("items", []) if i]}
                    )

            for card in (raw.get("info_cards") or []):
                if isinstance(card, dict):
                    out["info_cards"].append(
                        {"label": ct(card.get("label", "")),
                         "content": ct(card.get("content", ""))}
                    )

            for co in (raw.get("callouts") or []):
                if isinstance(co, dict):
                    out["callouts"].append(
                        {"label": ct(co.get("label", "")),
                         "content": ct(co.get("content", ""))}
                    )

            out["sections"] = extract_sections(
                raw.get("sections") or raw.get("contents") or []
            )

            cta = raw.get("call_to_action", {})
            if isinstance(cta, dict):
                out["call_to_action"] = {
                    "headline":    ct(cta.get("headline", "")),
                    "description": ct(cta.get("description", "")),
                    "button_text": ct(cta.get("button_text", "")),
                }
        elif isinstance(raw, list):
            out["sections"] = extract_sections(raw)

        logger.info(
            f"✅ Normalised: {len(out['sections'])} sections | "
            f"{len(out['info_cards'])} cards | {len(out['callouts'])} callouts | "
            f"{len(out['pull_quotes'])} quotes | {len(out['stats'])} stats"
        )
        return out

    # ── Content guarantee layer ───────────────────────────────────────────────

    def ensure_section_content(
        self,
        sections: List[Dict[str, str]],
        signals: Dict[str, str],
        firm_profile: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """
        Guarantees exactly 10 sections, each with ≥100 chars.
        Pads missing sections then parallel-regenerates thin ones.
        """
        FALLBACKS = [
            "Strategic Foundation", "Market Analysis", "Implementation Framework",
            "Performance Optimisation", "Risk Management", "Competitive Positioning",
            "Operational Excellence", "Future Roadmap", "Best Practices", "Action Plan",
        ]
        while len(sections) < 10:
            i = len(sections)
            sections.append({"title": FALLBACKS[i] if i < len(FALLBACKS) else f"Section {i+1}",
                              "content": ""})

        MIN = 100
        thin = [i for i, s in enumerate(sections)
                if len(str(s.get("content", "")).strip()) < MIN]

        if not thin:
            logger.info(f"✅ All {len(sections)} sections healthy.")
            return sections

        logger.info(f"⚠️  Regenerating {len(thin)} thin sections: {thin}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(thin), 5)) as ex:
            futures = {
                ex.submit(
                    self.regenerate_section_content,
                    sections[i]["title"], signals, firm_profile
                ): i for i in thin
            }
            for fut in concurrent.futures.as_completed(futures):
                i = futures[fut]
                try:
                    new = fut.result()
                    if new and len(new) >= MIN:
                        sections[i]["content"] = new
                        logger.info(f"  ✅ Section {i} ok ({len(new)} chars)")
                    else:
                        raise Exception(f"Thin regen output for section {i}")
                except Exception as e:
                    logger.error(f"  ❌ Section {i} regen failed: {e}")
                    raise

        return sections

    def regenerate_section_content(
        self,
        title: str,
        signals: Dict[str, str],
        firm_profile: Dict[str, Any],
    ) -> str:
        prompt = (
            f"Write a 150-220 word professional section for a strategic guide.\n"
            f"Section title: \"{title}\"\n"
            f"Topic: {signals.get('main_topic','Strategy')} | "
            f"Audience: {signals.get('target_audience','Professionals')} | "
            f"Firm: {firm_profile.get('firm_name','Expert Firm')}\n\n"
            "Write full paragraphs. No bullets. Expert tone. "
            "No JSON. No heading. Output ONLY the section text."
        )
        try:
            r = requests.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={"model": "sonar",
                      "messages": [
                          {"role": "system",
                           "content": "You are a professional content strategist."},
                          {"role": "user", "content": prompt},
                      ],
                      "max_tokens": 600, "temperature": 0.7},
                timeout=20,
            )
            r.raise_for_status()
            text = (r.json().get('choices', [{}])[0]
                    .get('message', {}).get('content', '').strip())
            text = re.sub(r'^#+\s*.*?\n', '', text)
            text = re.sub(r'\*+', '', text)
            return text
        except Exception as e:
            logger.error(f"regenerate_section_content('{title}'): {e}")
            return ""

    # ── Color helper ──────────────────────────────────────────────────────────

    def _derive_colors(self, hex_color: str) -> Dict[str, str]:
        if not (hex_color and hex_color.startswith('#') and len(hex_color) == 7):
            return {}
        try:
            r, g, b = (int(hex_color[1:3], 16),
                       int(hex_color[3:5], 16),
                       int(hex_color[5:7], 16))
            return {k: f"rgba({r},{g},{b},{a})"
                    for k, a in [("10", 0.1), ("20", 0.2), ("40", 0.4),
                                 ("60", 0.6), ("80", 0.8)]}
        except Exception:
            return {}

    # ── Template variable mapping ─────────────────────────────────────────────

    def map_to_template_vars(
        self,
        ai_content: Dict[str, Any],
        firm_profile: Optional[Dict[str, Any]] = None,
        user_answers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Maps normalised AI output to EVERY {{variable}} in magazine-template-v5.html.
        14 pages, 200+ variables.  Nothing left as a raw placeholder.
        """
        if not isinstance(ai_content, dict):
            ai_content = {}
        firm_profile  = firm_profile  or {}
        user_answers  = user_answers  or {}

        # ── Firm metadata ─────────────────────────────────────────────────────
        company   = str(firm_profile.get("firm_name")             or "Expert Firm").strip()
        email     = str(firm_profile.get("work_email")            or "").strip()
        phone     = str(firm_profile.get("phone_number")          or "").strip()
        website   = str(firm_profile.get("firm_website")          or "").strip()
        primary   = str(firm_profile.get("primary_brand_color")   or "#2a5766")
        secondary = str(firm_profile.get("secondary_brand_color") or "#B8860B")

        # ── Content arrays ────────────────────────────────────────────────────
        sections = ai_content.get("sections", [])
        if not isinstance(sections, list):
            sections = []
        while len(sections) < 10:
            sections.append({"title": f"Section {len(sections)+1}", "content": ""})

        def st(i: int, fb: str = "") -> str:
            return str((sections[i] if i < len(sections) else {}).get("title")   or fb).strip()

        def sc(i: int, fb: str = "") -> str:
            return str((sections[i] if i < len(sections) else {}).get("content") or fb).strip()

        insights   = ai_content.get("key_insights", []) or []
        quotes     = ai_content.get("pull_quotes",  []) or []
        checklists = ai_content.get("checklists",   []) or []
        cards      = ai_content.get("info_cards",   []) or []
        callouts   = ai_content.get("callouts",     []) or []
        stats      = ai_content.get("stats",        {}) or {}
        cta        = ai_content.get("call_to_action", {}) or {}

        def ins(i: int, fb: str = "") -> str:
            return str(insights[i]) if i < len(insights) else fb

        def quo(i: int, fb: str = "") -> str:
            return str(quotes[i]) if i < len(quotes) else fb

        def cli(si: int, ii: int, fb: str = "") -> str:
            if si < len(checklists):
                items = checklists[si].get("items", [])
                return str(items[ii]) if ii < len(items) else fb
            return fb

        def cl(i: int, fb: str = "") -> str:   # card label
            return str((cards[i] if i < len(cards) else {}).get("label")   or fb)

        def cc(i: int, fb: str = "") -> str:   # card content
            return str((cards[i] if i < len(cards) else {}).get("content") or fb)

        def ol(i: int, fb: str = "") -> str:   # callout label
            return str((callouts[i] if i < len(callouts) else {}).get("label")   or fb)

        def oc(i: int, fb: str = "") -> str:   # callout content
            return str((callouts[i] if i < len(callouts) else {}).get("content") or fb)

        def sv(k: str, fb: str = "") -> str:   # stat value
            return str(stats.get(k) or fb)

        # ── Title / headline ──────────────────────────────────────────────────
        def clean_sig(s: Any) -> str:
            if not isinstance(s, str): return ""
            return s.replace("REINTERPRET: ", "") if s.startswith("REINTERPRET") else s

        raw_title  = str(ai_content.get("title") or "").strip()
        main_topic_clean = clean_sig(user_answers.get('main_topic',''))
        main_title = raw_title or f"{main_topic_clean} Guide".strip()
        if not main_title or main_title.lower() == "guide":
            main_title = "Strategic Expert Guide"
            
        summary    = str(ai_content.get("summary")           or "A comprehensive strategic guide.").strip()
        outcome    = str(ai_content.get("outcome_statement") or summary).strip()
        hl_parts   = main_title.split(":", 1)
        hl1        = hl_parts[0].strip()
        hl2        = hl_parts[1].strip() if len(hl_parts) > 1 else "Professional Report"
        year       = str(datetime.now().year)

        # ═════════════════════════════════════════════════════════════════════
        # COMPLETE VARIABLE MAP  (aligns 1-to-1 with every {{…}} in v5 template)
        # ═════════════════════════════════════════════════════════════════════
        v: Dict[str, Any] = {

            # ── Global ───────────────────────────────────────────────────────
        "mainTitle":        main_title,
        "documentTitle":    main_title.upper(),
            "documentSubtitle": summary,
            "companyName":      company,
            "emailAddress":     email,
            "phoneNumber":      phone,
            "website":          website,
            "footerText":       f"© {year} {company}",

            # ── Colors (v5 uses color-mix() — only 2 base vars required) ─────
            "primaryColor":   primary,
            "secondaryColor": secondary,

            # ── PAGE 1 — COVER ───────────────────────────────────────────────
            "coverSeriesLabel":   "EXECUTIVE SERIES",
            "coverEyebrow":       "STRATEGIC ANALYSIS",
            "coverHeadlineLine1": hl1,
            "coverHeadlineLine2": hl2,
            "coverHeadlineLine3": company,
            "coverTagline":       (outcome[:80] + "…") if len(outcome) > 80 else outcome,
            "stat1Value":   "100%",  "stat1Label": "PROFESSIONAL",
            "stat2Value":   "AI",    "stat2Label": "OPTIMISED",
            "stat3Value":   year,    "stat3Label": "EDITION",

            # ── PAGE 2 — TERMS / INTRO ───────────────────────────────────────
            "sectionTitle1":      "Introduction",
            "pageNumber2":        "2",
            "termsHeadlineLine1": "Strategic",
            "termsHeadlineLine2": "Perspective",
            "termsParagraph1":    summary,
            "termsParagraph2":    "This guide provides expert insights to facilitate professional growth and strategic alignment.",
            "termsPullQuote":     quo(0, "Strategy is not about being different, but about making a difference."),
            "termsParagraph3":    "Our approach combines data-driven analysis with practical implementation frameworks.",
            "termsParagraph4":    "We empower organisations to navigate complexity with clarity and purpose.",

            # ── PAGE 3 — TABLE OF CONTENTS ───────────────────────────────────
            "sectionTitle2":  "Contents",
            "pageNumber3":    "3",
            "tocHeadlineLine1": "Strategic",
            "tocHeadlineLine2": "Roadmap",
            "tocSubtitle":    "An overview of the key insights and frameworks in this guide.",
            "contentItem1":   st(0, "Foundations"),        "contentItem1Sub":  "Setting the stage",
            "contentItem2":   st(1, "Strategic Overview"),  "contentItem2Sub":  "The landscape of opportunity",
            "contentItem3":   st(2, "Core Framework"),      "contentItem3Sub":  "Principles for excellence",
            "contentItem4":   st(3, "Implementation"),      "contentItem4Sub":  "Driving measurable impact",
            "contentItem5":   st(4, "Competitive Edge"),    "contentItem5Sub":  "Turning vision into reality",
            "contentItem6":   st(5, "Performance Metrics"), "contentItem6Sub":  "Measuring what matters",
            "contentItem7":   st(6, "Risk & Resilience"),   "contentItem7Sub":  "Protecting long-term value",
            "contentItem8":   st(7, "Operational Excellence"),"contentItem8Sub":"Sustaining the advantage",
            "contentItem9":   st(8, "Future Roadmap"),      "contentItem9Sub":  "Planning what's next",
            "contentItem10":  st(9, "Action Plan"),         "contentItem10Sub": "Your path forward",
            "pageNumber4":  "4",  "pageNumber5":  "5",  "pageNumber6":  "6",
            "pageNumber7":  "7",  "pageNumber8":  "8",  "pageNumber9":  "9",
            "pageNumber10": "10", "pageNumber11": "11", "pageNumber12": "12",
            "pageNumber13": "13",

            # ── PAGE 4 — CHAPTER 1  (★ HERO IMAGE) ──────────────────────────
            "sectionLabel3":   "CHAPTER 01",
            "chapterLabel1":   "01",
            "customTitle1":    st(0),
            "customContent1":  sc(0),
            "customContent1b": ins(0, ""),
            "imageLabel1":     "STRATEGY HERO",
            "imageCaption1":   "Mapping the path to strategic alignment.",
            "subheading1":     "Core Insight",
            "subcontent1":     ins(1, "Sustainable growth demands a balance of innovation and operational discipline."),
            "calloutLabel1":   ol(0, "KEY TAKEAWAY"),
            "calloutContent1": oc(0, "Success is measured by clarity of intent and consistency of execution."),

            # ── PAGE 5 — CHAPTER 2 ───────────────────────────────────────────
            "sectionLabel4":   "CHAPTER 02",
            "chapterLabel2":   "02",
            "customTitle2":    st(1),
            "customContent2":  sc(1),
            "pullQuote1":      quo(0, "The organisations that lead tomorrow invest in strategic clarity today."),
            "subheading2":     "Analysis",
            "subcontent2":     "Deep-dive analysis reveals hidden opportunities within your current framework.",
            "listItem1":       cli(0, 0, "Identify core value drivers across your portfolio"),
            "listItem2":       cli(0, 1, "Optimise resource allocation for maximum efficiency"),
            "listItem3":       cli(0, 2, "Enhance stakeholder engagement through structured frameworks"),
            "listItem4":       cli(0, 3, "Measure, iterate, and refine continuously"),
            "listFollowup2":   "By following these steps, organisations achieve a more resilient operational model.",

            # ── PAGE 6 — CHAPTER 3  (★ MEDIUM IMAGE) ────────────────────────
            "sectionLabel5":    "CHAPTER 03",
            "chapterLabel3":    "03",
            "customTitle3":     st(2),
            "customContent3":   sc(2),
            "imageLabel2":      "OPERATIONAL VIEW",
            "imageCaption2":    "Visualising the components of successful execution.",
            "page6Stat1Value":  sv("s1v", "85%"),  "page6Stat1Desc": sv("s1l", "Improvement in alignment"),
            "page6Stat2Value":  sv("s2v", "2.4x"), "page6Stat2Desc": sv("s2l", "Increase in efficiency"),
            "page6Stat3Value":  sv("s3v", "10k"),  "page6Stat3Unit": "+",
            "page6Stat3Desc":   sv("s3l", "Data points analysed"),
            "subheading3":      "Framework",
            "subcontent3":      "Our proven framework simplifies complex challenges into actionable strategic pillars.",
            "infoBoxLabel1":    cl(0, "QUICK TIP"),
            "infoBoxContent1":  cc(0, "Always validate your assumptions against real-world performance metrics."),

            # ── PAGE 7 — CHAPTER 4 ───────────────────────────────────────────
            "sectionLabel6":    "CHAPTER 04",
            "chapterLabel4":    "04",
            "customTitle4":     st(3),
            "customContent4":   sc(3),
            "colCard1Title":    cl(1, "INNOVATION"),
            "colCard1Content":  cc(1, "Staying ahead requires a culture of continuous learning and adaptation."),
            "colCard2Title":    cl(2, "AGILITY"),
            "colCard2Content":  cc(2, "The ability to pivot quickly is the ultimate competitive advantage."),
            "subheading4":      "Best Practices",
            "subcontent4":      "Consistency is the bridge between goals and accomplishment.",
            "calloutLabel2":    ol(1, "PRO TIP"),
            "calloutContent2":  oc(1, "Automate routine tasks to free up bandwidth for high-value strategic work."),

            # ── PAGE 8 — CHAPTER 5  (★ BANNER IMAGE) ────────────────────────
            "sectionLabel7":    "CHAPTER 05",
            "chapterLabel5":    "05",
            "customTitle5":     st(4),
            "customContent5":   sc(4),
            "imageLabel3":      "PERFORMANCE VIEW",
            "imageCaption3":    "Tracking progress against strategic objectives.",
            "subheading5":      "Implementation Steps",
            "numberedItem1":    cli(1, 0, "Establish baseline performance metrics"),
            "numberedItem2":    cli(1, 1, "Deploy structured governance frameworks"),
            "numberedItem3":    cli(1, 2, "Integrate continuous monitoring systems"),
            "numberedItem4":    cli(1, 3, "Report outcomes to senior stakeholders"),
            "infoBoxLabel2":    cl(3, "EXPERT NOTE"),
            "infoBoxContent2":  cc(3, "Organisations with clear KPI frameworks consistently outperform peers."),
            "infoBoxLabel3":    cl(4, "STRATEGY TIP"),
            "infoBoxContent3":  cc(4, "Align performance metrics with long-term strategic objectives for maximum impact."),

            # ── PAGE 9 — CHAPTER 6 ───────────────────────────────────────────
            "sectionLabel8":    "CHAPTER 06",
            "chapterLabel6":    "06",
            "customTitle6":     st(5),
            "customContent6":   sc(5),
            "pullQuote2":       quo(1, "Clarity of purpose transforms complexity into competitive advantage."),
            "page9Stat1Value":  sv("s4v", "3x"),   "page9Stat1Desc": sv("s4l", "ROI on strategic investment"),
            "page9Stat2Value":  sv("s5v", "67"),   "page9Stat2Unit": "%",
            "page9Stat2Desc":   sv("s5l", "Faster project delivery"),
            "page9Stat3Value":  sv("s6v", "92"),   "page9Stat3Unit": "%",
            "page9Stat3Desc":   sv("s6l", "Client satisfaction rate"),
            "subheading6":      "Strategic Outcomes",
            "subcontent6":      ins(2, "Organisations investing in strategic clarity consistently outperform peers."),
            "subcontent6b":     ins(3, "Sustained advantage requires both innovation and disciplined execution."),
            "calloutLabel3":    ol(2, "EXPERT NOTE"),
            "calloutContent3":  oc(2, "The firms that lead their markets build systems, not just capabilities."),

            # ── PAGE 10 — CHAPTER 7 ──────────────────────────────────────────
            "sectionLabel9":    "CHAPTER 07",
            "pageNumber10":     "10",
            "chapterLabel7":    "07",
            "customTitle7":     st(6),
            "customContent7":   sc(6),
            "infoBoxLabel4":    cl(5, "RISK FRAMEWORK"),
            "infoBoxContent4":  cc(5, "A structured risk framework identifies vulnerabilities before they become liabilities."),
            "subheading7":      "Risk Mitigation Steps",
            "ch7ListItem1":     cli(2, 0, "Conduct a comprehensive risk landscape assessment"),
            "ch7ListItem2":     cli(2, 1, "Develop tiered contingency response protocols"),
            "ch7ListItem3":     cli(2, 2, "Embed risk monitoring into operational workflows"),
            "ch7ListItem4":     cli(2, 3, "Review and update risk registers quarterly"),
            "calloutLabel4":    ol(3, "STRATEGY INSIGHT"),
            "calloutContent4":  oc(3, "Proactive risk management is the hallmark of organisations built for long-term endurance."),

            # ── PAGE 11 — CHAPTER 8 ──────────────────────────────────────────
            "sectionLabel10":    "CHAPTER 08",
            "pageNumber11":      "11",
            "chapterLabel8":     "08",
            "customTitle8":      st(7),
            "customContent8":    sc(7),
            "customContent8b":   ins(4, "Operational excellence is the foundation upon which sustainable growth is built."),
            "page11Stat1Value":  sv("s7v", "40%"),  "page11Stat1Desc": sv("s7l", "Reduction in operational costs"),
            "page11Stat2Value":  sv("s8v", "5x"),   "page11Stat2Unit": "",
            "page11Stat2Desc":   sv("s8l", "Return on process optimisation"),
            "page11Stat3Value":  sv("s9v", "98"),   "page11Stat3Unit": "%",
            "page11Stat3Desc":   sv("s9l", "Compliance rate achieved"),
            "subheading8":       "Operational Pillars",
            "subcontent8":       "World-class operations require deliberate design, continuous improvement, and quality commitment.",
            "infoBoxLabel5":     cl(5, "PROCESS TIP"),
            "infoBoxContent5":   cc(5, "Map every critical process before optimising it — visibility precedes improvement."),
            "infoBoxLabel6":     cl(6, "SYSTEMS NOTE"),
            "infoBoxContent6":   cc(6, "Integrated systems reduce friction and create compounding efficiency gains over time."),

            # ── PAGE 12 — CHAPTER 9 ──────────────────────────────────────────
            "sectionLabel11":    "CHAPTER 09",
            "pageNumber12":      "12",
            "chapterLabel9":     "09",
            "customTitle9":      st(8),
            "customContent9":    sc(8),
            "pullQuote3":        quo(2, "The future belongs to organisations that prepare for it deliberately and decisively."),
            "colCard5Title":     cl(0, "SHORT-TERM"),
            "colCard5Content":   cc(0, "Quick wins that build momentum and demonstrate early value to stakeholders."),
            "colCard6Title":     cl(1, "LONG-TERM"),
            "colCard6Content":   cc(1, "Structural investments that compound over time and create durable competitive moats."),
            "subheading9":       "Future Milestones",
            "ch9ListItem1":      cli(2, 0, "Define 12-month priorities with measurable targets"),
            "ch9ListItem2":      cli(2, 1, "Align resources and budgets with declared priorities"),
            "ch9ListItem3":      cli(2, 2, "Establish governance cadence and accountability structures"),
            "subcontent9":       "Strategic foresight combined with operational readiness positions organisations to lead through change.",

            # ── PAGE 13 — CHAPTER 10 ─────────────────────────────────────────
            "sectionLabel12":    "CHAPTER 10",
            "pageNumber13":      "13",
            "chapterLabel10":    "10",
            "customTitle10":     st(9),
            "customContent10":   sc(9),
            "customContent10b":  outcome,
            "page13Stat1Value":  sv("s1v", "85%"),  "page13Stat1Desc": sv("s1l", "Success rate with structured approach"),
            "page13Stat2Value":  sv("s2v", "2.4x"), "page13Stat2Unit": "",
            "page13Stat2Desc":   sv("s2l", "Faster time-to-value"),
            "page13Stat3Value":  sv("s3v", "10k"),  "page13Stat3Unit": "+",
            "page13Stat3Desc":   sv("s3l", "Professionals guided"),
            "subheading10":      "Your Immediate Next Steps",
            "subcontent10":      "Turn these insights into action with a structured 90-day implementation sprint.",
            "calloutLabel5":     ol(4, "CRITICAL POINT"),
            "calloutContent5":   oc(4, "The greatest risk is not acting on knowledge — execution is the ultimate differentiator."),
            "infoBoxLabel7":     cl(6, "ACTION GUIDE"),
            "infoBoxContent7":   cc(6, "Schedule your strategic planning session within 30 days to capitalise on these insights."),

            # ── PAGE 14 — CLOSING / CTA ──────────────────────────────────────
            "sectionLabelCTA":    "NEXT STEPS",
            "pageNumberCTA":      "14",
            "chapterLabelCTA":    "TAKE ACTION",
            "ctaHeadlineLine1":   "Ready to",
            "ctaHeadlineLine2":   "Take Action?",
            "ctaEyebrow":         "NEXT STEPS",
            "ctaTitle":           str(cta.get("headline")    or "Start Your Journey"),
            "ctaText":            str(cta.get("description") or "We are ready to help you turn these insights into measurable growth."),
            "ctaButtonText":      str(cta.get("button_text") or "Connect Now"),
            "contactLabel1":      "EMAIL",    "contactValue1": email,
            "contactLabel2":      "PHONE",    "contactValue2": phone,
            "contactLabel3":      "WEB",      "contactValue3": website,
            "differentiatorTitle":"Why Work With Us",
            "differentiator":     outcome,
            "colCardCTA1Title":   cl(0, "OUR APPROACH"),
            "colCardCTA1Content": cc(0, "We combine expertise with data-driven frameworks to deliver measurable outcomes."),
            "colCardCTA2Title":   cl(1, "YOUR OUTCOME"),
            "colCardCTA2Content": cc(1, "Clients who engage with our frameworks see transformative results within 90 days."),
        }

        logger.info(f"✅ Mapped {len(v)} template variables | title='{main_title[:50]}'")
        return v

    # ── Misc ──────────────────────────────────────────────────────────────────

    def generate_slogan(
        self, user_answers: Dict[str, Any], firm_profile: Dict[str, Any]
    ) -> str:
        prompt = (
            f"Generate a professional slogan under 10 words.\n"
            f"Firm: {firm_profile.get('firm_name','Expert Firm')}\n"
            f"Topic: {user_answers.get('main_topic','Strategy')}\n"
            f"Audience: {user_answers.get('target_audience','Professionals')}"
        )
        try:
            r = requests.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={"model": "sonar",
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 50},
                timeout=5,
            )
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            logger.error(f"Slogan error: {e}")
            return ""

    def check_available_models(self):
        if not self.api_key:
            print("❌ PERPLEXITY_API_KEY not configured")
            return
        try:
            r = requests.get(
                "https://api.perplexity.ai/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if r.status_code == 200:
                for m in r.json().get('data', []):
                    print(f"  - {m['id']}")
            else:
                print(f"❌ {r.status_code}: {r.text}")
        except Exception as e:
            print(f"❌ {e}")
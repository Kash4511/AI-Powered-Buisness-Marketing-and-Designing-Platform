import os
import sys
import json
from typing import Any, Dict, List, Tuple
from jinja2 import Environment, FileSystemLoader, nodes
from jinja2.visitor import NodeVisitor
root_mod = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_mod not in sys.path:
    sys.path.append(root_mod)
from lead_magnets.perplexity_client import PerplexityClient


class Ref:
    def __init__(self, base: str, path: List[str], ctx: str, lineno: int, filters: List[str], default: Any):
        self.base = base
        self.path = path
        self.ctx = ctx
        self.lineno = lineno
        self.filters = filters
        self.default = default

    def key(self) -> str:
        return ".".join([self.base] + self.path) if self.path else self.base


class Mapper(NodeVisitor):
    def __init__(self):
        self.refs: List[Ref] = []

    def _extract(self, node, ctx: str, filters: List[str] = None, default: Any = None) -> List[Ref]:
        filters = filters or []
        res: List[Ref] = []
        if isinstance(node, nodes.Name):
            res.append(Ref(node.name, [], ctx, getattr(node, "lineno", 0), filters, default))
        elif isinstance(node, nodes.Getattr):
            parts = []
            obj = node
            while isinstance(obj, nodes.Getattr):
                parts.insert(0, obj.attr)
                obj = obj.node
            if isinstance(obj, nodes.Name):
                res.append(Ref(obj.name, parts, ctx, getattr(node, "lineno", 0), filters, default))
            else:
                res.extend(self._extract(obj, ctx, filters, default))
        elif isinstance(node, nodes.Getitem):
            base_parts = []
            obj = node
            while isinstance(obj, nodes.Getitem):
                key = obj.arg.name if isinstance(obj.arg, nodes.Name) else None
                if isinstance(obj.arg, nodes.Const):
                    base_parts.insert(0, str(obj.arg.value))
                elif key:
                    base_parts.insert(0, key)
                else:
                    base_parts.insert(0, "[]")
                obj = obj.node
            if isinstance(obj, nodes.Name):
                res.append(Ref(obj.name, base_parts, ctx, getattr(node, "lineno", 0), filters, default))
            else:
                res.extend(self._extract(obj, ctx, filters, default))
        elif isinstance(node, nodes.Filter):
            f = node.name
            new_filters = filters + [f]
            dval = default
            if f == "default":
                args = getattr(node, "args", [])
                if args and isinstance(args[0], nodes.Const):
                    dval = args[0].value
            res.extend(self._extract(node.node, ctx, new_filters, dval))
        elif isinstance(node, nodes.Call):
            if node.node:
                res.extend(self._extract(node.node, ctx, filters, default))
            for a in node.args or []:
                res.extend(self._extract(a, ctx, filters, default))
            for _, kw in node.kwargs or []:
                res.extend(self._extract(kw, ctx, filters, default))
        elif isinstance(node, nodes.Test):
            res.extend(self._extract(node.node, ctx, filters, default))
        elif isinstance(node, nodes.Tuple):
            for x in node.items:
                res.extend(self._extract(x, ctx, filters, default))
        elif isinstance(node, nodes.Concat):
            for x in node.nodes:
                res.extend(self._extract(x, ctx, filters, default))
        elif isinstance(node, nodes.BinExpr):
            res.extend(self._extract(node.left, ctx, filters, default))
            res.extend(self._extract(node.right, ctx, filters, default))
        elif isinstance(node, nodes.UnaryExpr):
            res.extend(self._extract(node.node, ctx, filters, default))
        return res

    def visit_Output(self, node: nodes.Output):
        for child in node.nodes:
            self.refs.extend(self._extract(child, "output"))

    def visit_If(self, node: nodes.If):
        self.refs.extend(self._extract(node.test, "if_test"))
        for child in node.body:
            self.visit(child)
        for child in node.else_ or []:
            self.visit(child)

    def visit_For(self, node: nodes.For):
        self.refs.extend(self._extract(node.iter, "for_iter"))
        for child in node.body:
            self.visit(child)
        for child in node.else_ or []:
            self.visit(child)

    def visit_Filter(self, node: nodes.Filter):
        self.refs.extend(self._extract(node, "filter"))

    def visit_Getattr(self, node: nodes.Getattr):
        self.refs.extend(self._extract(node, "getattr"))

    def visit_Getitem(self, node: nodes.Getitem):
        self.refs.extend(self._extract(node, "getitem"))

    def visit_Name(self, node: nodes.Name):
        self.refs.extend(self._extract(node, "name"))


def analyze_template(template_dir: str, template_name: str) -> Dict[str, Any]:
    env = Environment(loader=FileSystemLoader(template_dir))
    src = env.loader.get_source(env, template_name)[0]
    ast = env.parse(src)
    mapper = Mapper()
    mapper.visit(ast)
    usage: Dict[str, Dict[str, Any]] = {}
    for ref in mapper.refs:
        key = ref.key()
        entry = usage.setdefault(key, {"name": key, "usages": [], "filters": set(), "defaults": []})
        entry["usages"].append({"context": ref.ctx, "line": ref.lineno})
        for f in ref.filters:
            entry["filters"].add(f)
        if ref.default is not None:
            entry["defaults"].append(ref.default)
    for v in usage.values():
        v["filters"] = sorted(list(v["filters"]))
        v["defaults"] = list(v["defaults"])
    return {"template": template_name, "variables": sorted(usage.values(), key=lambda x: x["name"])}


def infer_type_from_usages(name: str, usages: List[Dict[str, Any]]) -> str:
    if "image" in name.lower() or "url" in name.lower() or "logo" in name.lower():
        return "string:url"
    if "pageNumber" in name or "Value" in name:
        return "number|string"
    if "Title" in name or "Subtitle" in name or "Label" in name or "Text" in name or "Content" in name:
        return "string"
    return "string"


def add_types(mapping: Dict[str, Any]) -> Dict[str, Any]:
    for v in mapping["variables"]:
        v["type"] = infer_type_from_usages(v["name"], v["usages"])
        v.setdefault("default", None)
        if v["defaults"]:
            v["default"] = v["defaults"][0]
    return mapping


def generate_sample_vars() -> Dict[str, Any]:
    client = PerplexityClient()
    firm = {
        "firm_name": "Forma Studio",
        "work_email": "studio@example.com",
        "phone_number": "555-0100",
        "firm_website": "https://example.com",
        "primary_brand_color": "#334",
        "secondary_brand_color": "#556",
        "industry": "Architecture",
    }
    answers = {
        "lead_magnet_type": "guide",
        "main_topic": "sustainable-architecture",
        "target_audience": ["Architects/Peers", "Contractors"],
        "audience_pain_points": ["budget", "timeline", "compliance"],
        "desired_outcome": "",
        "call_to_action": "",
        "special_requests": "",
        "lead_magnet_description": "A professional guide for sustainable projects."
    }
    try:
        ai_content = client.generate_lead_magnet_json(answers, firm)
    except Exception:
        cover = {"title": "Sustainable Architecture", "subtitle": "", "company_name": firm["firm_name"]}
        contents = {"title": "Contents", "items": ["Overview", "Details", "Strategy", "Analysis", "Implementation"]}
        sections = [
            {"title": "Overview", "content": "Expanded guidance."},
            {"title": "Details", "content": "Expanded guidance."},
            {"title": "Strategy", "content": "Expanded guidance."},
            {"title": "Analysis", "content": "Expanded guidance."},
            {"title": "Implementation", "content": "Expanded guidance."},
        ]
        contact = {"title": "Contact & Next Steps", "email": firm["work_email"], "phone": firm["phone_number"], "website": firm["firm_website"]}
        terms = {"title": "Terms of Use", "summary": "", "paragraphs": [""]}
        ai_content = {"style": {}, "cover": cover, "contents": contents, "sections": sections, "contact": contact, "terms": terms, "brand": {"logo_url": ""}}
    template_vars = client.map_to_template_vars(ai_content, firm, answers)
    return template_vars


def validate(mapping: Dict[str, Any], sample_vars: Dict[str, Any]) -> Dict[str, Any]:
    names = [v["name"] for v in mapping["variables"]]
    missing = [n for n in names if n not in sample_vars]
    unused = [k for k in sample_vars.keys() if k not in names]
    return {"missing_in_sample": missing, "unused_in_template": unused}


def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lead_magnets", "templates"))
    template_name = "Template.html"
    mapping = analyze_template(base, template_name)
    mapping = add_types(mapping)
    sample_file = None
    if len(sys.argv) > 1:
        sample_file = sys.argv[1]
    if sample_file and os.path.exists(sample_file):
        with open(sample_file, "r", encoding="utf-8") as f:
            sample_vars = json.load(f)
    else:
        sample_vars = generate_sample_vars()
    report = validate(mapping, sample_vars)
    out = {
        "mapping": mapping,
        "validation": report
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
